import datetime
from pathlib import Path
import re

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from ......stream_collection_scripts.GEANT.run import run as run_geant
from ......stream_collection_scripts.Internet2.run import run as run_i2
from ...models import Stream


class Command(BaseCommand):
    help = "Scrape the looking glasses and import streams onto the site."

    def handle(self, *args, **kwargs):
        devices_path = str(Path(__file__).resolve().parent.parent.parent.parent.parent.parent + "/stream_collection")

        results_dictionary_list = []
        results_dictionary_list.append(run_geant(devices_path + "/GEANT/devices.txt"))
        results_dictionary_list.append(run_i2(devices_path + "/Internet2/devices.txt"))

        scrape_user = get_user_model().objects.get_or_create(
            username="DEFAULT_SCRAPING_USER"
        )[0]

        for results in results_dictionary_list:
            if results["source"] not in ["193.17.9.3", "193.17.9.7"]:  # filter out Eumsat
                if re.match("^[0-9.]+$", results["source"]):  # filter out IPv6
                    if results["pps"] > 100:  # filter out low pps
                        Stream.objects.update_or_create(
                            source=results["source"], 
                            group=results["group"],
                            owner=scrape_user,
                            defaults={
                                "pps": results["pps"],
                                "active": True,
                                "last_seen": datetime.datetime.now(),
                                "whois": results["who_is"],
                            }
                        )
