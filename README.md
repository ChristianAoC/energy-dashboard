# Energy Dashboard with Context Explorer

The goal of this dashboard is to allow users to contextualise energy data. A description of the origins and research intentions can be found on the [Net0i project website](https://wp.lancs.ac.uk/net0i/energy-dashboard/), and a paper/poster explaining its use can be [accessed here](https://wp.lancs.ac.uk/net0i/files/2025/06/2025-remy-contextviz.pdf). A public demo is available here: [https://christianremy.com/dashboard/](https://christianremy.com/dashboard/)

# Setup Instructions

You can download/fork/checkout the repository to run and test locally. There is a Dockerfile to simplify setup, but if you decide to run it in a testing environment (e.g., VSCode) make sure you have the required Python pages in `requirements.txt` installed in your virtual environment.

A typical installation with Docker goes as follows (make sure Docker and Git are installed):

1) `sudo git clone https://github.com/ChristianAoC/energy-dashboard/`
2) `sudo docker build -t energy-dashboard .`
3) `sudo docker compose down`
4) `sudo docker compose up -d`

You can check if the Docker container is running with `sudo docker logs energy-dashboard`.

As the first action, you will have to create the admin user before continuing the setup. Navigate to the URL you've deployed to and go to the settings page (click on the cogwheel in the top right). The first user will be activated and logged in automatically and be admin - so make sure you do this instantly after deployment. If someone got their before you first, delete the `data/data.sqlite` file and register.

After registration, you will upload some files. Go to settings -> upload files in the dashboard and upload a metadata and a polygon file. The benchmark file is optional and included in the release, so don't worry about that for now. You will also need offline files or set up the database endpoint to feed the dashboard. You can find an offline dataset along with the metadata and a polygon file under releases in the sidebar of this repository. The offline files need to be uploaded onto your deployment server into the /data/offline folder, metadata and polygons you can upload via the dashboard (or upload along with the offline files into the data folder).

If you don't use offline data, you can define Influx database connectors in the system variables under settings.

For more users to sign up, they will need email authentication. If your server doesn't support some built-in SMTP and you need to set up a new account, the usual way to go about it is to create a GMail account. Just make sure to enable 2FA and then create an app password for logging in. Then enter the Gmail SMTP information again under system variables.

For ease of deployment some settings for credentials can be read from an `.env` file instead (will be automatically imported upon first initialisation, i.e., when no SQLite DB can be found). For available settings and explanations refer to `.env.template`.

## Funding

The research behind this project was funded by the [UKRI](https://gtr.ukri.org/projects?ref=EP%2FT025964%2F1), grant no EP/T025964/1, and with the official project name "Reducing End Use Energy Demand in Commercial Settings Through Digital Innovation". The informal and commonly used name for this project was Net Zero insights.

## License

This project is licensed under the [MIT License](LICENSE).  
You are free to use, modify, and distribute this software for any purpose, including commercial use, as long as you include the original copyright.

Please note that this software is provided "as is", without any warranty.
