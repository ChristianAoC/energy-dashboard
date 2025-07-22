# dashboard

A dashboard to explore energy data, originally developed for the [Net0i project](https://wp.lancs.ac.uk/net0i/), funded by the [UKRI project EP/T025964/1](https://gow.epsrc.ukri.org/NGBOViewGrant.aspx?GrantRef=EP/T025964/1).

## Notes

The original version of this tool was used internally. The public code in this repository tries to make as much as possible to be available for public use. It comes with a small subset of anonymised data, energy data from 2024 for several buildings, such that the dashboard's functionality can be explored without any additional input. While there is a login system and user level functionality, comments can be made anonymously.

## Requirements and additional files

Required python packages can be found in `requirements.txt`. The tool was tested in a coding environment (VSCode) as well as deployed on web servers (Docker, and before manually via Apache on Ubuntu and Debian).

Note that the `data` subdirectory needs to have write permissions for the app (e.g., www-data or whichever user owns the Flask app/web server). All data is stored in there. If you use the Dockerfile, mount a data folder into the docker container. Add the persistent release data (in the sidebar of this repo) such as the anonomised offline data and its metadata to the relevant folders in data.

By default, the dashboard pulls data from `data/anon` as per meta information found in the `data/meta_anon` files. To connect your own data to the tool, mirror the meta files and put them in a folder `data/internal_meta`, and then either connect the Influx backend using the Influx variables in the `.env` file, or (to use offline data) mirror the format of the files in `data/anon` and put them in an `data/offline`. While attempts have been made to make the backend flexible to other data streams, energy data is rarely standardised and as such adaptions in `api/api.py` are likely to be necessary.

There is also a map overview, however, it needs Mazemap coordinates as well as the buildings to be mapped to the data in the meta file (there is no automated process for it - it requires manual editing) as well as the building polygons in `dashboard/static/data/allBuildings.js`. The provided buildings are for the Lancaster University campus in the UK.

User data is stored in a file called `data/users.json` which will be automatically created as soon as the first user signs up.

Context information, i.e., annotations and comments made in the dashboard, are stored in a JSON file `data/context.json`. It will be automatically created when the first context element is entered.

## .env file settings

The `.env.template` file shows available environment variables. If not present, the dashboard should still run normally as there are default settings for most relevant environment variables (like a random string for the app's secret key).

There is a separate `SMPT_ENABLED` setting for development purposes - while SMTP information is available the mailer module can be temporarily disabled to avoid spamming SMTP during development testing.

If your server doesn't support some built-in SMTP and you need to set up a new account, the usual way to go about it is to create a GMail account. Just make sure to enable 2FA and then create an app password for logging in.

If you don't want or cannot set an STMP host for email confirmation, it is recommended to use the demo account feature. By setting `DEMO_EMAIL_DOMAINS` to a domain such as "dashboard.demo", only emails in the form of "username@dashboard.demo" will be allowed, but activated immediately without confirmation. This was originally set up for demo purposes but still allows different user names to add context (if not logged in, context events are attributed to "anonymous").

If you are part of an organisation, it might be advisable to restrict emails to one or several particular domains, using the `REQUIRED_EMAIL_DOMAINS` variable.

## Deployment

Once you've created/downloaded/edited all files (.env and data releases) start the dashboard depending on your deployment preferences - e.g., `flask run` for development settings, adjusting your Apache settings, or, recommended, by deploying via Docker and mounting /data and .env externally:

```
docker build -t energy-dashboard .

docker run --env-file /path/on/host/.env \
  -v /path/on/host/data:/app/data \
  -d -p 80:5000 energy-dashboard
```

Make sure the paths to your .env file and data directories are correct, default data is present, and both ports 80 and 5000 are open in your firewall.

## License

This project is licensed under the [MIT License](LICENSE).  
You are free to use, modify, and distribute this software for any purpose, including commercial use, as long as you include the original copyright.

Please note that this software is provided "as is", without any warranty.
