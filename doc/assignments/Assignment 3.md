You should write a scraper for the class webpages (from Assignment 1), using BeautifulSoup, Scrapy or rvest. I have posted (in the class git) the scraping code we discussed, which is using BeautifulSoup. Class webpages can be found in downloaded_class_submissions.zip in the class git.

Your grade will be based off of all output of the scraped file tables being stored in *data/assignment_3/altered/parsed_bios.sqllite*

With two tables:

*favorites*:

| favorite_id | name_id | category  | favorite      |
| ----------- | ------- | --------- | ------------- |
| 1           | 1       | Sport     | Rock Climbing |
| 2           | 1       | Ice Cream | Coffee        |
| ...         | ...     | ...       | ...           |

*names*:

| name_id | name      |
| ------- | --------- |
| 1       | Ephy Love |
| ...     | ...       |

