from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.db import models, transaction
from django.db.models import F
from django.db.transaction import get_connection
from django.utils import timezone

from multicast.settings import TRENDING_STREAM_USAGE_WEIGHT, TRENDING_STREAM_MAX_SIZE, TRENDING_STREAM_INIT_SCORE


class Category(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField()

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name


class Stream(models.Model):
    id = models.AutoField(primary_key=True)

    COLLECTION_METHODS = (("01", "Scraping"), ("02", "Manual"), ("03", "Upload"), ("04", "API"))

    # Administrative
    active = models.BooleanField(default=True)
    collection_method = models.CharField(max_length=2, choices=COLLECTION_METHODS, null=True, blank=True)
    owner = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, null=True, blank=True)

    # Stream
    amt_relay = models.CharField(max_length=100, null=True, blank=True)
    group = models.GenericIPAddressField(null=True, blank=True)
    source = models.GenericIPAddressField(null=True, blank=True)
    udp_port = models.IntegerField(null=True, blank=True)

    # Display
    categories = models.ManyToManyField(Category, blank=True)
    description = models.CharField(max_length=100, null=True, blank=True)
    report_count = models.IntegerField(default=0)
    source_name = models.CharField(max_length=100, null=True, blank=True)
    thumbnail = models.ImageField(null=True, blank=True, upload_to="stream_previews/%Y/%m/%d/%H")
    preview = models.ImageField(null=True, blank=True, upload_to="stream_previews/%Y/%m/%d/%H")
    editors_choice = models.BooleanField(default=False)
    likes = models.ManyToManyField(User, related_name="liked_streams", blank=True)
    """
    A relationship which indicates that a stream was once liked by a user and then the like was removed.
    The relationship is used to check if this is the first time a stream is liked by a user.
    Any further likes of the same stream from the same user will not increase its trending score again.
    """
    removed_likes = models.ManyToManyField(User, related_name="unliked_streams", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "{} (Source: {}, Group: {})".format(self.get_description(), self.source, self.group)

    # Returns the owner's description, if set, otherwise returns the most popular user description
    def get_description(self):
        if self.description:
            return self.description
        elif self.user_description_set.all():
            return self.user_description_set.order_by("-votes")[0]
        else:
            return "No description available"

    # Returns the last time this stream's collection object was updated
    def get_time_last_found(self):
        if self.collection_method == "01":
            return self.scraping.time
        elif self.collection_method == "02":
            return self.manual.time
        elif self.collection_method == "03":
            return self.upload.time
        elif self.collection_method == "04":
            return self.api.time
        return None

    # Updates the "time" field on this stream's collection object
    def update_last_found(self):
        new_time = timezone.now()
        if self.collection_method == "01":
            self.scraping.time = new_time
            self.scraping.save()
        elif self.collection_method == "02":
            self.manual.time = new_time
            self.manual.save()
        elif self.collection_method == "03":
            self.upload.time = new_time
            self.upload.save()
        elif self.collection_method == "04":
            self.api.time = new_time
            self.api.save()

    # Allow users to report broken streams
    def report(self):
        self.report_count += 1
        if self.report_count > 10:
            self.active = False
        self.save()

    # Returns the URL address of the stream
    def get_url(self):
        url = "amt://" + self.source + "@" + self.group
        if self.udp_port:
            url = url + ":" + str(self.udp_port)
        return url


class Description(models.Model):
    id = models.AutoField(primary_key=True)

    # Administration
    stream = models.ForeignKey(Stream, on_delete=models.CASCADE, related_name="user_description_set")
    user_submitted = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)

    # Display
    text = models.CharField(max_length=100)
    votes = models.IntegerField(default=0)

    def __str__(self):
        return "{}".format(self.text)

    # Increase the count of votes
    def upvote(self):
        self.votes += 1
        self.save()

    # Decrease the count of votes
    def downvote(self):
        self.votes -= 1
        self.save()


class TrendingStreamManager(models.Manager):
    """
    Custom manager for the trending streams.
    Provides a method through which Stream objects can be added to the trending stream table.
    In order to have the trending streams working properly, it is important to NOT create
    TrendingStream objects directly with the create() method, but to always add the Stream
    objects to the trending streams table through the add() method, which ensures that the whole
    trending streams table is correctly updated.
    """

    def add(self, stream):
        """
        Adds a Stream object to the trending stream table.

        This is an implementation of the LRFU (Least Recently/Frequently Used) cache replacement policy.
        The policy directly seeks to combine LRU (Least Recently Used) and LFU (Least Frequently Used)
        to expire trending streams based on a formula that combines both recency and frequency of use.

        References:

        [1] frequently and most recently used items ranking algorithm,
        https://stackoverflow.com/questions/41716033/frequently-and-most-recently-used-items-ranking-algorithm

        [2]  Donghee Lee et al.,
        "LRFU: a spectrum of policies that subsumes the least recently used and least frequently used policies,"
        in IEEE Transactions on Computers, vol. 50, no. 12, pp. 1352-1361, Dec. 2001, doi: 10.1109/TC.2001.970573.

        :param stream: Stream to be added to the trending stream table
        :return: None
        """
        # Start an atomic transaction
        with transaction.atomic():
            # Lock the whole table for the transaction, so that other transactions cannot get executed simultaneously
            # Make sure not to lock, when sqlite is used, because it does not support locking!!!
            cursor = get_connection().cursor()
            if settings.DATABASES['default']['ENGINE'] != 'django.db.backends.sqlite3':
                cursor.execute(f'LOCK TABLE {self.model._meta.db_table}')
            try:
                # Get all trending streams from the table
                trending_streams = TrendingStream.objects.all()
                # Update the score of all existing trending streams
                trending_streams.update(score=F("score") * TRENDING_STREAM_USAGE_WEIGHT)
                # Search for the input stream in the trending table
                found = trending_streams.filter(stream_id=stream.id).first()
                if found is None:
                    # The stream was not found in the trending table
                    if trending_streams.count() < TRENDING_STREAM_MAX_SIZE:
                        # We have room -> Add the stream to the trending table
                        TrendingStream.objects.create(stream=stream, score=TRENDING_STREAM_INIT_SCORE)
                    else:
                        # No more room -> Delete the last trending stream and add the input stream to the trending table
                        last_trending_stream = trending_streams.last()
                        if last_trending_stream:
                            last_trending_stream.delete()
                        TrendingStream.objects.create(stream=stream, score=TRENDING_STREAM_INIT_SCORE)
                else:
                    # If the input stream already exists in the trending table -> Increment its score
                    found.score = found.score + TRENDING_STREAM_INIT_SCORE
                    found.save()

                # Get the trending streams, calculate the new rankings and update the table at once
                trending_streams = TrendingStream.objects.all()
                for index, trending_stream in enumerate(trending_streams):
                    trending_stream.ranking = index + 1
                TrendingStream.objects.bulk_update(trending_streams, ['ranking'])
            finally:
                cursor.close()


class TrendingStream(models.Model):
    stream = models.OneToOneField(Stream, on_delete=models.CASCADE, related_name="trending_stream")
    score = models.FloatField()
    ranking = models.IntegerField(default=101)

    objects = TrendingStreamManager()

    class Meta:
        ordering = ("-score",)

    def __str__(self):
        return "{:.3f}: {}".format(self.score, self.stream.get_description())
