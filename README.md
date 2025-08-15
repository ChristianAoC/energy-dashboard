# Energy Dashboard with Context Explorer

The goal of this dashboard is to allow users to contextualise energy data. A description of the origins and research intentions can be found on the [Net0i project website](https://wp.lancs.ac.uk/net0i/energy-dashboard/), and a paper/poster explaining its use can be [accessed here](https://wp.lancs.ac.uk/net0i/files/2025/06/2025-remy-contextviz.pdf). A public demo is available here: [https://christianremy.com/dashboard/](https://christianremy.com/dashboard/)

# Setup Instructions

You can download/fork/checkout the repository to run and test locally. There is a Dockerfile to simplify setup, but if you decide to run it in a testing environment (e.g., VSCode) make sure you have the required Python packages in `requirements.txt` installed in your virtual environment.

A typical installation with Docker goes as follows (make sure Docker and Git are installed):

1) `sudo git clone https://github.com/ChristianAoC/energy-dashboard/`
2) `sudo docker build -t energy-dashboard .`
3) `sudo docker compose up -d`

You can check if the container is running with `sudo docker compose ps`. Also check for any error messages in `sudo docker logs energy-dashboard`.

> [!NOTE]
> For ease of deployment, you can optionally define some settings in a `.env` file. An example file is provided with in the repo and explains what each setting does.
> Any settings that aren't provided in the file are given default values that can be edited later.
>
> The `.env` file is only used for initial setup, it won't be kept up-to-date with any changes made in the dashboard and vice-vera.

As the first action, you will have to create the admin user before continuing the setup. Navigate to the URL you've deployed to and go to the settings page (the cogwheel in the top right of the dashboard). The first user will be activated and logged in automatically and have admin level permissions - so make sure you do this quickly after deployment. If someone got there before you, delete the `data/data.sqlite` file, restart the container and try again.

After registration, you will need to upload some files. Go to Settings > Upload Files and upload a metadata and a polygon file. The benchmark file is already included in the release, so don't worry about that for now. You will also need to either provide offline files or to set up the database endpoint to feed the dashboard (If you haven't done so already).

You can find an example dataset along with the metadata and a polygon file [under releases in the sidebar of the GitHub repository](https://github.com/ChristianAoC/energy-dashboard/releases/latest). The offline files need to be uploaded onto your server into the `./data/offline/` folder, metadata and polygons can uploaded via the dashboard (or upload along with the offline files into the data folder).

> [!IMPORTANT]
> If you manually upload a metadata (.xlsx) file, you need to go to one of these endpoints to initialise them. You need to log into an account with admin level permissions to access the endpoints.
> - If this is the first metadata file to be initialised (metadata files are automatically initialised when uploaded in the dashboard), go to: `<hostname>/api/populate-database`
> - If this is not the first time, or you are unsure, go to: `<hostname>/api/regenerate-offline-metadata`

If you don't use offline data, you can define Influx database connectors in the system variables under settings (If you haven't already defined them in the `.env` file).

For more users to sign up, they will need email authentication. If your server doesn't support some built-in SMTP and you need to set up a new account, the easiest way to do this is to create a GMail account. Make sure to enable 2FA and then create an app password for logging in. Then enter the Gmail SMTP information again under system variables (If you haven't already defined them in the `.env` file).

# General Info

The idea, requirements elicitation, data and knowledge gathering, user testing, and initial coding was done by [Christian Remy](https://github.com/ChristianAoC/). While the project started in 2022, coding began in mid-2024. Most of the work was done in Jupyter Notebooks and private Github repositories which is why the codebase doesn't reflect the first few iterations. Since August 2025, the main developer and maintainer is [Luke Needle](https://github.com/LukeNeedle) who initially refactored and reconceptualised the backend and now holds the reins.

Other contributors were [Adrian Friday](https://github.com/adrianfriday) (project's main PI and oversight), [Paul Smith](https://github.com/waternumbers) (initial data API and statistical analysis), [Oliver Bates](https://github.com/oscarechobravo) (qualitative research collaborator), [Christina Bremer](https://github.com/ChristinaBre) (Figma sketches), and [Adam Tyler](https://github.com/adam-tyler-lancaster) (data maintainer at Lancaster University).

## Funding

The research behind this project was funded by the [UKRI](https://gtr.ukri.org/projects?ref=EP%2FT025964%2F1), grant no. `EP/T025964/1` awarded to  Prof. Adrian Friday at Lancaster University. The official project name was "Reducing End Use Energy Demand in Commercial Settings Through Digital Innovation", but in academic contexts this project was labeled "Net Zero insights".

## License

This project is licensed under the [MIT License](LICENSE).  
You are free to use, modify, and distribute this software for any purpose, including commercial use, as long as you include the original copyright.

Please note that this software is provided "as is", without any warranty.
