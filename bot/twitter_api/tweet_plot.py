import os
import sys
import time
import random
import logging
import requests
import datetime
import multiprocessing
import matplotlib.pyplot as plt
from twitter_api.api_keys import Keys
from requests_oauthlib import OAuth1
from plotting.random_plot_generator import random_plot_generator
from utils.tweet_text_generator import tweet_text_generator


media_endpoint_url = 'https://upload.twitter.com/1.1/media/upload.json'
post_tweet_url = 'https://api.twitter.com/1.1/statuses/update.json'

keys = Keys()

oauth = OAuth1(
    keys.CONSUMER_KEY,
    client_secret=keys.CONSUMER_SECRET,
    resource_owner_key=keys.ACCESS_TOKEN,
    resource_owner_secret=keys.ACCESS_TOKEN_SECRET
)


# Official Twitter API example by Twitter Developer Relations:
# https://github.com/twitterdev/large-video-upload-python
class Tweet(object):

    def __init__(self, testing=False, choice=None):
        """
        Defines video tweet properties
        """
        # create a random GIF
        while True:
            manager = multiprocessing.Manager()
            return_dict = manager.dict()

            choice_list = [
                # "degradation comparison (summary variables)",
                "non-degradation comparisons"
            ]
            if choice is None:
                choice = random.choice(choice_list)

            p = multiprocessing.Process(target=random_plot_generator, args=(
                return_dict,
                {
                    "testing": testing,
                    "choice": choice,
                    "chemistry": None,
                    "provided_degradation": True
                }
            )
            )

            p.start()
            # time-out
            p.join(1200)

            if p.is_alive():    # pragma: no cover
                print(
                    "Simulation is taking too long, "
                    + "KILLING IT and starting a NEW ONE."
                )
                p.kill()
                p.join()
            else:   # pragma: no cover
                break

        if os.path.exists("plot.gif"):
            self.plot = "plot.gif"
        else:
            self.plot = "plot.png"
        self.total_bytes = os.path.getsize(self.plot)
        self.media_id = None
        self.processing_info = None
        self.config = None
        self.model = return_dict["model"]
        self.chemistry = return_dict["chemistry"]
        self.is_experiment = return_dict["is_experiment"]
        self.cycle = return_dict["cycle"]
        self.number = return_dict["number"]
        self.is_comparison = return_dict["is_comparison"]
        if choice == "non-degradation comparisons":
            self.param_to_vary = return_dict["param_to_vary"]
            self.varied_values = return_dict["varied_values"]
            self.params = return_dict["params"]
        else:
            self.param_to_vary = None
            self.varied_values = None
            self.params = None
        self.testing = testing

    def upload_init(self):
        """
        Initializes Upload
        """
        print('INIT')

        # initiate uploading the data
        if os.path.exists("plot.gif"):
            request_data = {
                'command': 'INIT',
                'media_type': 'image/gif',
                'total_bytes': self.total_bytes,
                'media_category': 'tweet_gif'
            }
        else:
            request_data = {
                'command': 'INIT',
                'media_type': 'image/png',
                'total_bytes': self.total_bytes,
                'media_category': 'tweet_image'
            }

        # post the initial request
        req = self.post_request(media_endpoint_url, request_data, oauth)

        # extract media id for the GIF
        media_id = req.json()['media_id']

        self.media_id = media_id

        print('Media ID: %s' % str(media_id))

    def upload_append(self):
        """
        Uploads media in chunks and appends to chunks uploaded
        """
        segment_id = 0
        bytes_sent = 0
        file = open(self.plot, 'rb')

        # upload the media in chunks
        while bytes_sent < self.total_bytes:

            # initialise a single chunk
            chunk = file.read(4*1024*1024)

            print('APPEND')

            # append the chunks
            request_data = {
                'command': 'APPEND',
                'media_id': self.media_id,
                'segment_index': segment_id
            }

            files = {
                'media': chunk
            }

            # post request to append the chunks
            self.post_request(media_endpoint_url, request_data, oauth, files)

            segment_id = segment_id + 1
            bytes_sent = file.tell()

            print(
                '%s of %s bytes uploaded' % (
                    str(bytes_sent),
                    str(self.total_bytes)
                )
            )

        print('Upload chunks complete.')
        file.close()

    def upload_finalize(self):
        """
        Finalizes uploads and starts video processing
        """
        print('FINALIZE')

        # finalize the media upload
        request_data = {
            'command': 'FINALIZE',
            'media_id': self.media_id
        }

        # send a request for finalizing the media upload
        req = self.post_request(media_endpoint_url, request_data, oauth)

        print(req.json())

        # extract the processing information of the GIF and check status
        # until it either passes or fails
        self.processing_info = req.json().get('processing_info', None)
        self.check_status()

    def check_status(self):
        """
        Checks video processing status
        """
        if self.processing_info is None:    # pragma: no cover
            return

        state = self.processing_info['state']

        print('Media processing status is %s ' % state)

        if state == u'succeeded':
            return

        if state == u'failed':  # pragma: no cover
            sys.exit(0)

        check_after_secs = self.processing_info['check_after_secs']

        print('Checking after %s seconds' % str(check_after_secs))
        time.sleep(check_after_secs)

        print('STATUS')

        request_params = {
            'command': 'STATUS',
            'media_id': self.media_id
        }

        req = requests.get(
            url=media_endpoint_url, params=request_params, auth=oauth
        )

        self.processing_info = req.json().get('processing_info', None)
        self.check_status()

    def post_request(self, url, data, auth, files=None):
        """
        Posts a request on the Twitter API and makes
        sure that the given post request succeeds
        """
        # logging configs
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)

        # try to post request, if the API gives an error, sleep for 5 minutes
        # and then try again
        while True:
            if files is None:
                req = requests.post(
                    url=url,
                    data=data,
                    auth=auth
                )
            else:
                req = requests.post(
                    url=url,
                    data=data,
                    files=files,
                    auth=auth
                )
            if (
                req.status_code >= 200 and req.status_code <= 299
            ):
                break
            else:  # pragma: no cover
                logger.info(req.status_code)
                logger.info(req.text)
                logger.info(
                    "Twitter API internal error."
                    + " Trying again in 5 minutes"
                )
                time.sleep(300)

        return req

    def write_config(self, filename, append=False):    # pragma: no cover
        """
        Writes the random config to config.txt and appends the same to
        data.txt with date and time.
        """
        # the configuration for the GIF
        self.config = {
            "model": str(self.model),
            "model options": self.model.options
            if not isinstance(self.model, dict)
            else None,
            "chemistry": self.chemistry,
            "is_experiment": self.is_experiment,
            "cycle": self.cycle,
            "number": self.number,
            "is_comparison": self.is_comparison,
            "param_to_vary": self.param_to_vary,
            "varied_values": self.varied_values
        }

        # append to data.txt and write to config.txt
        if not append:
            f = open(filename, "w")
            f.write(str(self.config))
        elif append:
            f = open(filename, "a")
            f.write(
                str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                + " " + str(self.config)
                + "\n"
            )
        f.close()

    def tweet(self):
        """
        Publishes Tweet with attached plot
        """
        # generate a text for the tweet
        tweet_status, experiment = (
            tweet_text_generator(
                self.chemistry,
                self.model,
                self.is_experiment,
                self.cycle,
                self.number,
                self.is_comparison,
                self.param_to_vary,
                self.params
            )
        )
        print(tweet_status)

        # data for the GIF tweet
        request_data = {
            'status': tweet_status,
            'media_ids': self.media_id
        }

        if not self.testing:    # pragma: no cover
            # tweet the GIF
            req = self.post_request(post_tweet_url, request_data, oauth)

            # write the config in txt files for users to reproduce
            self.write_config("config.txt")
            self.write_config("data.txt", append=True)

            # reply to the posted tweet
            if experiment is not None:  # pragma: no cover
                reply = {
                    'status': experiment,
                    'in_reply_to_status_id': req.json()['id'],
                    'auto_populate_reply_metadata': True
                }

                # post reply
                self.post_request(post_tweet_url, reply, oauth)

        if os.path.exists("plot.gif"):
            os.remove("plot.gif")
        if os.path.exists("plot.png"):
            os.remove("plot.png")
        plt.close()


if __name__ == '__main__':  # pragma: no cover
    tweet = Tweet()
    tweet.upload_init()
    tweet.upload_append()
    tweet.upload_finalize()
    if not tweet.testing:
        time.sleep(random.randint(0, 3600))
    tweet.tweet()