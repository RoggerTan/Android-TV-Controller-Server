# Android-TV-Controller-API-Server

This API server receives commands and send signals to the specified Android TV box as a remote control. 

Although it is known to be much faster than Android Debug Bridge method (ADB), not all TV boxes are compatible. 

## 1. Preparations
**Step 1: Create Python 3 virtual environment (venv), install all required packages, and activate (venv).**

It's a good practice to run as separate, new user. 

```
sudo adduser androidtvcontroller
```

Store all files in **/home/androidtvcontroller/**. 

**Step 2: Generate certificate.**

```
python3 certificate_generator.py
```

**Step 3: Deploy the server**

Take a look at configs/server.json. if isDeployed is false, the app will run in debug mode at 127.0.0.1. Unless there's something wrong, you should just ignore it. You may need to update *boxIp* value also. 

Create /etc/systemd/system/androidtvcontroller.service with Nano or any other text editor: 

```
[Unit]
Description=Android TV Controller
After=network.target

[Service]
ExecStart=/bin/bash /home/androidtvcontroller/startup.sh
WorkingDirectory=/home/androidtvcontroller
StandardOutput=inherit
StandardError=inherit
User=androidtvcontroller

[Install]
WantedBy=multi-user.target
```

Now, enable and run the service!

```
sudo systemctl enable androidtvcontroller
sudo systemctl start androidtvcontroller
```

That will run the API server. Here are all the paths: 

- /signal [GET]: Receive command to signal the box. 
    - Example: /signal?key=h : Return to Android TV Home. 
- /startpairing [GET]: Start the pairing procedure. The PIN code will appear on TV. 
- /pairing [GET]: Finish pairing. The server needs to receive the PIN code. 
    - Example: /pairing?secret=25T3

NOTE: There's no way to create certificate via API request for now. Thus, you must deploy the *.pem files created at step 2 along with the Python codes. 

**Step 4: Combine with other apps (optional)**

Home Assistant: Use [shell Command](https://www.home-assistant.io/integrations/shell_command/) in [configuration.yaml](https://www.home-assistant.io/docs/configuration/). 

```
shell_command:
    box_home: curl --location --request GET 'http://0.0.0.0:5011/signal?key=h'
    box_back: curl --location --request GET 'http://0.0.0.0:5011/signal?key=b'
    box_startpairing: curl --location --request GET 'http://0.0.0.0:5011/startpairing'
    box_pairing: curl --location --request GET http://0.0.0.0:5011/pairing?secret={{states('input_text.box_secret')}}
    ...
```

## 2. Credits

The project uses work from farshid616's [Android-TV-Remote-Controller-Python](https://github.com/farshid616/Android-TV-Remote-Controller-Python). 
