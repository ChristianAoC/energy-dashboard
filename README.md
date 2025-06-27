# dashboard

A dashboard to explore energy data, originally developed for the [Net0i project](https://wp.lancs.ac.uk/net0i/), funded by the [UKRI project EP/T025964/1](https://gow.epsrc.ukri.org/NGBOViewGrant.aspx?GrantRef=EP/T025964/1).

## Notes

The original version of this tool was used internally. The public code in this repository tries to make as much as possible to be available for public use. It comes with a small subset of anonymised data, energy data from 2024 for several buildings, such that the dashboard's functionality can be explored without any additional input. While there is a login system and user level functionality, comments can be made anonymously.

## Setup instructions and requirements

Required python packages can be found in `requirements.txt`. The tool was tested in a coding environment (VSCode) as well as deployed on web servers (Apache on Ubuntu and Debian).

Note that the base directory as well as the `data/health_check` subdirectory need to have write permissions for the app (e.g., www-data or whichever user owns the Flask app/web server).

By default, it pulls data from `data/anon` as per meta information found in the `data/meta_anon` files. To connect your own data to the tool, mirror the meta files and put them in a folder `data/internal_meta`, and then either connect the Influx backend using the Influx variables in the `.env` file, or (to use offline data) mirror the format of the files in `data/anon` and put them in an `data/offline`. While attempts have been made to make the backend flexible to other data streams, energy data is rarely standardised and as such adaptions in `api/api.py` are likely to be necessary.

There is also a map overview, however, it needs Mazemap coordinates as well as the buildings to be mapped to the data in the meta file (there is no automated process for it - it requires manual editing) as well as the building polygons in `dashboard/static/data/allBuildings.js`. The provided buildings are for the Lancaster University campus in the UK.

User data is stored in a file called `users.json` which will be automatically created as soon as the first user signs up.

Context information, i.e., annotations and comments made in the dashboard, are stored in a JSON file `context.json`. It will be automatically created when the first context element is entered.

## .env file settings

Please check the `app.py` and `api/api.py` for available .env variables to configure the app. All variables that are required to run the dashboard have default settings, so the environment file is optional, but highly recommended, especially to set the app secret key. Here are selected important .env variables explained:

`SECRET_KEY` is required for Flask session/cookie management.

`SITE_NAME` is the app's name in the browser and in emails (if sent out).

`OFFLINE_MODE` disables the database backend connection and instead looks for files in the `data/offline` folder (make sure the meta files in `data/internal_meta` match accordingly).

`ANON_MODE` is used for demo purposes to obfuscate internal identifiers and allows for a separate, second data set, e.g., for demo purposes.

```
MAZEMAP_CAMPUS_ID = 123
MAZEMAP_LNG = "12.3456"
MAZEMAP_LAT = "12.3456"
```

Sets the Mazemap location, if available (defaults to the Lancaster campus if not set).

```
INFLUX_URL = "www.influxdb.url"
INFLUX_PORT = 1234
INFLUX_USER = "username"
INFLUX_PASS = "password"
```

Enables the Influx database connection. Note that this assumes Influx 1.8 (databases with measurements, not buckets as in Influx 2.0).

User management is not a mandatory part, but quite essential:

```
SMTP_ADDRESS = 'email@host.com'
STMP_PASSWORD = 'password'
SMTP_SERVER = 'smtp.domain.com'
SMTP_PORT = 587
SMTP_ENABLED = True
```

There is a separate `SMPT_ENABLED` setting for development purposes - while SMTP information is available the mailer module can be temporarily disabled to avoid spamming SMTP during development testing.

If your server doesn't support some built-in SMTP and you need to set up a new account, the usual way to go about it is to create a GMail account. Just make sure to enable 2FA and then create an app password for logging in.

If you don't want or cannot set an STMP host for email confirmation, it is recommended to use the demo account feature. By setting

`DEMO_EMAIL_DOMAINS` to a domain such as "dashboard.demo", only emails in the form of "username@dashboard.demo" will be allowed, but activated immediately without confirmation. This was originally set up for demo purposes but still allows different user names to add context (if not logged in, context events are attributed to "anonymous").

If you are part of an organisation, it might be advisable to restrict emails to one or several particular domains, using the `REQUIRED_EMAIL_DOMAINS` variable.

Last but not least, you can specify user levels to restrict access to certain parts and functions of the dashboard. For more on that check `app.py` (for basic settings) as well as `dashboard/main.py` (to set additional user levels for specific routes). By default, everyone can see all parts of the dashboard and add comments, but not edit/delete comments.
