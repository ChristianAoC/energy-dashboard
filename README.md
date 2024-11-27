# dashboard

A dashboard to explore energy data, originally developed for the [Net0i project](https://wp.lancs.ac.uk/net0i/).

## Notes

The original version of this tool is to be used internally only. The public code in this repository tries to make as much as possible to be available for public use.

## Setup environment variables

As usual the Flask app needs a secret key, this is to be set in a `.env` file in the root directory:

```
SECRET_KEY = 'abcdefghijklmnopqrstuvwxyz'
```

You can also set a site name, which will be used in the browser's title and emails being sent out:

```
SITE_NAME = "Energy Dashboard"
```

The map feature defaults to the random Mazemap demo campus. You can set a campus ID and the coordinates:

```
MAZEMAP_CAMPUS_ID = 123
MAZEMAP_LNG = "12.3456"
MAZEMAP_LAT = "12.3456"
```

Currently, the API connects to an Influx database (version 1.8, note it is significantly different from any version 2.0 and higher):

```
INFLUX_URL = 'www.influxdb.url'
INFLUX_PORT = 123
INFLUX_USER = 'username'
INFLUX_PASS = 'password'
```

User access data is stored in an SQLite file `database.db`. The schema to create it can be found in `SCHEMA-database.db`.

Context information, i.e., annotations and comments made in the dashboard, are stored in a JSON file `context.json`. It will be automatically created when the first context element is entered.

User management is not a mandatory part, but quite essential:

```
SMTP_ADDRESS = 'email@host.com'
STMP_PASSWORD = 'password'
SMTP_SERVER = 'smtp.domain.com'
SMTP_PORT = 587
```

If your server doesn't support some built-in SMTP and you need to set up a new account, the usual way to go about it is to create a GMail account. Just make sure to enable 2FA and then create an app password for logging in.

The database file, `database.db`, will be created on first launch, so you don't have to worry about it. There is another file to store context and comments, `context.json`, which will also be created when needed.