import os
import sys
from datetime import datetime
from time import sleep
import json

import pandas as pd
from fake_headers import Headers
from progress import Progress
from scroller import Scroller
from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    WebDriverException,
)
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.support.ui import WebDriverWait
from tweet import Tweet
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager

TWITTER_LOGIN_URL = "https://twitter.com/i/flow/login"


class Twitter_Scraper:
    def __init__(
        self,
        mail,
        username,
        password,
        max_tweets=50,
        scrape_username=None,
        scrape_hashtag=None,
        scrape_query=None,
        scrape_poster_details=False,
        scrape_latest=True,
        scrape_top=False,
        proxy=None,
    ):
        print("Initializing Twitter Scraper...")
        self.mail = mail
        self.username = username
        self.password = password
        self.interrupted = False
        self.tweet_ids = set()
        self.data = []
        self.tweet_cards = []
        self.scraper_details = {
            "type": None,
            "username": None,
            "hashtag": None,
            "query": None,
            "tab": None,
            "poster_details": False,
        }
        self.max_tweets = max_tweets
        self.progress = Progress(0, max_tweets)
        self.router = self.go_to_home
        self.driver = self._get_driver(proxy)
        self.actions = ActionChains(self.driver)
        self.scroller = Scroller(self.driver)
        self._config_scraper(
            max_tweets,
            scrape_username,
            scrape_hashtag,
            scrape_query,
            scrape_latest,
            scrape_top,
            scrape_poster_details,
        )

    def _config_scraper(
        self,
        max_tweets=50,
        scrape_username=None,
        scrape_hashtag=None,
        scrape_query=None,
        scrape_latest=True,
        scrape_top=False,
        scrape_poster_details=False,
    ):
        self.tweet_ids = set()
        self.data = []
        self.tweet_cards = []
        self.max_tweets = max_tweets
        self.progress = Progress(0, max_tweets)
        self.scraper_details = {
            "type": None,
            "username": scrape_username,
            "hashtag": (
                str(scrape_hashtag).replace("#", "")
                if scrape_hashtag is not None
                else None
            ),
            "query": scrape_query,
            "tab": "Latest" if scrape_latest else "Top" if scrape_top else "Latest",
            "poster_details": scrape_poster_details,
        }
        self.router = self.go_to_home
        self.scroller = Scroller(self.driver)

        if scrape_username is not None:
            self.scraper_details["type"] = "Username"
            self.router = self.go_to_profile
        elif scrape_hashtag is not None:
            self.scraper_details["type"] = "Hashtag"
            self.router = self.go_to_hashtag
        elif scrape_query is not None:
            self.scraper_details["type"] = "Query"
            self.router = self.go_to_search
        else:
            self.scraper_details["type"] = "Home"
            self.router = self.go_to_home
        pass

    def _get_driver(
        self,
        proxy=None,
    ):
        print("Setup WebDriver...")
        header = Headers().generate()["User-Agent"]

        # browser_option = ChromeOptions()
        browser_option = FirefoxOptions()
        browser_option.add_argument("--no-sandbox")
        browser_option.add_argument("--disable-dev-shm-usage")
        browser_option.add_argument("--ignore-certificate-errors")
        browser_option.add_argument("--disable-gpu")
        browser_option.add_argument("--log-level=3")
        browser_option.add_argument("--disable-notifications")
        browser_option.add_argument("--disable-popup-blocking")
        browser_option.add_argument("--user-agent={}".format(header))
        if proxy is not None:
            browser_option.add_argument("--proxy-server=%s" % proxy)

        # For Hiding Browser

        try:
            # print("Initializing ChromeDriver...")
            # driver = webdriver.Chrome(
            #     options=browser_option,
            # )

            print("Initializing FirefoxDriver...")
            driver = webdriver.Firefox(
                options=browser_option,
            )

            print("WebDriver Setup Complete")
            return driver
        except WebDriverException:
            try:
                # print("Downloading ChromeDriver...")
                # chromedriver_path = ChromeDriverManager().install()
                # chrome_service = ChromeService(executable_path=chromedriver_path)

                print("Downloading FirefoxDriver...")
                firefoxdriver_path = GeckoDriverManager().install()
                firefox_service = FirefoxService(executable_path=firefoxdriver_path)

                # print("Initializing ChromeDriver...")
                # driver = webdriver.Chrome(
                #     service=chrome_service,
                #     options=browser_option,
                # )

                print("Initializing FirefoxDriver...")
                driver = webdriver.Firefox(
                    service=firefox_service,
                    options=browser_option,
                )

                print("WebDriver Setup Complete")
                return driver
            except Exception as e:
                print(f"Error setting up WebDriver: {e}")
                sys.exit(1)
        pass

    def login(self):
        print()
        print("Logging in to Twitter...")

        try:
            self.driver.maximize_window()
            self.driver.get(TWITTER_LOGIN_URL)
            sleep(3)

            self._input_username()
            self._input_unusual_activity()
            self._input_password()

            cookies = self.driver.get_cookies()

            auth_token = None

            for cookie in cookies:
                if cookie["name"] == "auth_token":
                    auth_token = cookie["value"]
                    break

            if auth_token is None:
                raise ValueError(
                    """This may be due to the following:

- Internet connection is unstable
- Username is incorrect
- Password is incorrect
"""
                )

            print()
            print("Login Successful")
            print()
        except Exception as e:
            print()
            print(f"Login Failed: {e}")
            sys.exit(1)

        pass

    def _input_username(self):
        input_attempt = 0

        while True:
            try:
                username = self.driver.find_element(
                    "xpath", "//input[@autocomplete='username']"
                )

                username.send_keys(self.username)
                username.send_keys(Keys.RETURN)
                sleep(3)
                break
            except NoSuchElementException:
                input_attempt += 1
                if input_attempt >= 3:
                    print()
                    print(
                        """There was an error inputting the username.

It may be due to the following:
- Internet connection is unstable
- Username is incorrect
- Twitter is experiencing unusual activity"""
                    )
                    self.driver.quit()
                    sys.exit(1)
                else:
                    print("Re-attempting to input username...")
                    sleep(2)

    def _input_unusual_activity(self):
        input_attempt = 0

        while True:
            try:
                unusual_activity = self.driver.find_element(
                    "xpath", "//input[@data-testid='ocfEnterTextTextInput']"
                )
                unusual_activity.send_keys(self.username)
                unusual_activity.send_keys(Keys.RETURN)
                sleep(3)
                break
            except NoSuchElementException:
                input_attempt += 1
                if input_attempt >= 3:
                    break

    def _input_password(self):
        input_attempt = 0

        while True:
            try:
                password = self.driver.find_element(
                    "xpath", "//input[@autocomplete='current-password']"
                )

                password.send_keys(self.password)
                password.send_keys(Keys.RETURN)
                sleep(3)
                break
            except NoSuchElementException:
                input_attempt += 1
                if input_attempt >= 3:
                    print()
                    print(
                        """There was an error inputting the password.

It may be due to the following:
- Internet connection is unstable
- Password is incorrect
- Twitter is experiencing unusual activity"""
                    )
                    self.driver.quit()
                    sys.exit(1)
                else:
                    print("Re-attempting to input password...")
                    sleep(2)

    def go_to_home(self):
        self.driver.get("https://twitter.com/home")
        sleep(3)
        pass

    def go_to_profile(self):
        if (
            self.scraper_details["username"] is None
            or self.scraper_details["username"] == ""
        ):
            print("Username is not set.")
            sys.exit(1)
        else:
            self.driver.get(f"https://twitter.com/{self.scraper_details['username']}")
            sleep(3)
        pass

    def go_to_hashtag(self):
        if (
            self.scraper_details["hashtag"] is None
            or self.scraper_details["hashtag"] == ""
        ):
            print("Hashtag is not set.")
            sys.exit(1)
        else:
            url = f"https://twitter.com/hashtag/{self.scraper_details['hashtag']}?src=hashtag_click"
            if self.scraper_details["tab"] == "Latest":
                url += "&f=live"

            self.driver.get(url)
            sleep(3)
        pass

    def go_to_search(self):
        if self.scraper_details["query"] is None or self.scraper_details["query"] == "":
            print("Query is not set.")
            sys.exit(1)
        else:
            url = f"https://twitter.com/search?q={self.scraper_details['query']}&src=typed_query"
            if self.scraper_details["tab"] == "Latest":
                url += "&f=live"

            self.driver.get(url)
            sleep(3)
        pass

    def get_tweet_cards(self):
        self.tweet_cards = self.driver.find_elements(
            "xpath", '//article[@data-testid="tweet" and not(@disabled)]'
        )
        pass

    def remove_hidden_cards(self):
        try:
            hidden_cards = self.driver.find_elements(
                "xpath", '//article[@data-testid="tweet" and @disabled]'
            )

            for card in hidden_cards[1:-2]:
                self.driver.execute_script(
                    "arguments[0].parentNode.parentNode.parentNode.remove();", card
                )
        except Exception as e:
            return
        pass

    def load_hashtags(self):
        hashtags_file = os.path.join(os.path.dirname(__file__), '..', '..', 'hashtags.json')
        if os.path.exists(hashtags_file):
            with open(hashtags_file, 'r') as f:
                return json.load(f)
        return []

    def scrape_tweets(
        self,
        max_tweets=50,
        no_tweets_limit=False,
        scrape_username=None,
        scrape_hashtag=None,
        scrape_query=None,
        scrape_latest=True,
        scrape_top=False,
        scrape_poster_details=False,
        router=None,
    ):
        hashtags = self.load_hashtags()
        if not hashtags:
            print("No hashtags found in hashtags.json. Skipping Twitter scraper run.")
            return

        for hashtag in hashtags:
            print(f"Scraping tweets for hashtag: {hashtag}")
            self._config_scraper(
                max_tweets=max_tweets,
                scrape_hashtag=hashtag,
                scrape_latest=scrape_latest,
                scrape_top=scrape_top,
                scrape_poster_details=scrape_poster_details,
            )
            self.router()

            # Accept cookies to make the banner disappear
            try:
                accept_cookies_btn = self.driver.find_element(
                    "xpath", "//span[text()='Refuse non-essential cookies']/../../.."
                )
                accept_cookies_btn.click()
            except NoSuchElementException:
                pass

            self.progress.print_progress(0, False, 0, no_tweets_limit)

            refresh_count = 0
            added_tweets = 0
            empty_count = 0
            retry_cnt = 0

            while self.scroller.scrolling:
                try:
                    self.get_tweet_cards()
                    added_tweets = 0

                    for card in self.tweet_cards[-15:]:
                        try:
                            tweet_id = str(card)

                            if tweet_id not in self.tweet_ids:
                                self.tweet_ids.add(tweet_id)

                                if not self.scraper_details["poster_details"]:
                                    self.driver.execute_script(
                                        "arguments[0].scrollIntoView();", card
                                    )

                                tweet = Tweet(
                                    card=card,
                                    driver=self.driver,
                                    actions=self.actions,
                                    scrape_poster_details=self.scraper_details[
                                        "poster_details"
                                    ],
                                )

                                if tweet:
                                    if not tweet.error and tweet.tweet is not None:
                                        if not tweet.is_ad:
                                            self.data.append(tweet.tweet)
                                            added_tweets += 1
                                            self.progress.print_progress(
                                                len(self.data), False, 0, no_tweets_limit
                                            )

                                            if (
                                                len(self.data) >= self.max_tweets
                                                and not no_tweets_limit
                                            ):
                                                self.scroller.scrolling = False
                                                break
                                        else:
                                            continue
                                    else:
                                        continue
                                else:
                                    continue
                            else:
                                continue
                        except NoSuchElementException:
                            continue

                    if len(self.data) >= self.max_tweets and not no_tweets_limit:
                        break

                    if added_tweets == 0:
                        # Check if there is a button "Retry" and click on it with a regular basis until a certain amount of tries
                        try:
                            while retry_cnt < 15:
                                retry_button = self.driver.find_element(
                                    "xpath", "//span[text()='Retry']/../../.."
                                )
                                self.progress.print_progress(
                                    len(self.data), True, retry_cnt, no_tweets_limit
                                )
                                sleep(58)
                                retry_button.click()
                                retry_cnt += 1
                                sleep(2)
                        # There is no Retry button so the counter is reseted
                        except NoSuchElementException:
                            retry_cnt = 0
                            self.progress.print_progress(
                                len(self.data), False, 0, no_tweets_limit
                            )

                        if empty_count >= 5:
                            if refresh_count >= 3:
                                print()
                                print("No more tweets to scrape")
                                break
                            refresh_count += 1
                        empty_count += 1
                        sleep(1)
                    else:
                        empty_count = 0
                        refresh_count = 0
                except StaleElementReferenceException:
                    sleep(2)
                    continue
                except KeyboardInterrupt:
                    print("\n")
                    print("Keyboard Interrupt")
                    self.interrupted = True
                    break
                except Exception as e:
                    print("\n")
                    print(f"Error scraping tweets: {e}")
                    break

            print("")

            if len(self.data) >= self.max_tweets or no_tweets_limit:
                print("Scraping Complete")
            else:
                print("Scraping Incomplete")

            if not no_tweets_limit:
                print("Tweets: {} out of {}\n".format(len(self.data), self.max_tweets))

            # After scraping one hashtag, save to JSON and wait for 1 minute
            print(f"Finished scraping for hashtag: {hashtag}")
            self.save_to_json()  # Add this line to save after each hashtag
            print("Waiting for 1 minute before processing the next hashtag...")
            sleep(60)

        # After all hashtags are processed
        print("Finished scraping all hashtags")

        pass

    def save_to_json(self):
        print("Starting save_to_json method...")
        now = datetime.now()
        
        # Create a 'tweets' folder in the same directory as the script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        folder_path = os.path.join(script_dir, '..', '..', 'tweets')

        print(f"Script directory: {script_dir}")
        print(f"Attempting to save to folder: {folder_path}")

        # Create the folder if it doesn't exist
        if not os.path.exists(folder_path):
            try:
                os.makedirs(folder_path)
                print(f"Created Folder: {folder_path}")
            except Exception as e:
                print(f"Error creating folder: {e}")
                return

        json_data = []
        print(f"Number of tweets to save: {len(self.data)}")

        for i, tweet in enumerate(self.data):
            try:
                tweet_dict = {
                    "Name": tweet[0],
                    "Handle": tweet[1],
                    "Timestamp": tweet[2],
                    "Verified": tweet[3],
                    "Content": tweet[4],
                    "Comments": tweet[5],
                    "Retweets": tweet[6],
                    "Likes": tweet[7],
                    "Analytics": tweet[8],
                    "Tags": tweet[9],
                    "Mentions": tweet[10],
                    "Emojis": tweet[11],
                    "Profile Image": tweet[12],
                    "Tweet Link": tweet[13],
                    "Tweet ID": f"tweet_id:{tweet[14]}"
                }

                if self.scraper_details["poster_details"]:
                    tweet_dict["Tweeter ID"] = f"user_id:{tweet[15]}"
                    tweet_dict["Following"] = tweet[16]
                    tweet_dict["Followers"] = tweet[17]

                json_data.append(tweet_dict)
            except Exception as e:
                print(f"Error processing tweet {i}: {e}")

        current_time = now.strftime("%Y-%m-%d_%H-%M-%S")
        file_name = f"{current_time}_tweets_1-{len(self.data)}.json"
        file_path = os.path.join(folder_path, file_name)

        print(f"Attempting to save file: {file_path}")

        try:
            with open(file_path, 'w', encoding='utf-8') as json_file:
                json.dump(json_data, json_file, ensure_ascii=False, indent=2)
            print(f"JSON Saved successfully: {file_path}")
        except Exception as e:
            print(f"Error saving JSON file: {e}")

        print("save_to_json method completed.")

    def get_tweets(self):
        return self.data

    def save_to_json(self):
        print("Starting save_to_json method...")
        now = datetime.now()
        
        # Create a 'tweets' folder in the same directory as the script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        folder_path = os.path.join(script_dir, '..', '..', 'tweets')

        print(f"Script directory: {script_dir}")
        print(f"Attempting to save to folder: {folder_path}")

        # Create the folder if it doesn't exist
        if not os.path.exists(folder_path):
            try:
                os.makedirs(folder_path)
                print(f"Created Folder: {folder_path}")
            except Exception as e:
                print(f"Error creating folder: {e}")
                return

        json_data = []
        print(f"Number of tweets to save: {len(self.data)}")

        for i, tweet in enumerate(self.data):
            try:
                tweet_dict = {
                    "Name": tweet[0],
                    "Handle": tweet[1],
                    "Timestamp": tweet[2],
                    "Verified": tweet[3],
                    "Content": tweet[4],
                    "Comments": tweet[5],
                    "Retweets": tweet[6],
                    "Likes": tweet[7],
                    "Analytics": tweet[8],
                    "Tags": tweet[9],
                    "Mentions": tweet[10],
                    "Emojis": tweet[11],
                    "Profile Image": tweet[12],
                    "Tweet Link": tweet[13],
                    "Tweet ID": f"tweet_id:{tweet[14]}"
                }

                if self.scraper_details["poster_details"]:
                    tweet_dict["Tweeter ID"] = f"user_id:{tweet[15]}"
                    tweet_dict["Following"] = tweet[16]
                    tweet_dict["Followers"] = tweet[17]

                json_data.append(tweet_dict)
            except Exception as e:
                print(f"Error processing tweet {i}: {e}")

        current_time = now.strftime("%Y-%m-%d_%H-%M-%S")
        file_name = f"{current_time}_tweets_1-{len(self.data)}.json"
        file_path = os.path.join(folder_path, file_name)

        print(f"Attempting to save file: {file_path}")

        try:
            with open(file_path, 'w', encoding='utf-8') as json_file:
                json.dump(json_data, json_file, ensure_ascii=False, indent=2)
            print(f"JSON Saved successfully: {file_path}")
        except Exception as e:
            print(f"Error saving JSON file: {e}")

        print("save_to_json method completed.")
