# GSUITE AUTOMATION UTILITIES

*Python version: 3.9.7*

**Before running this scripts you have to do the following steps:**

1. Create and activate a virtual environment:

```
(Mac)
$ python3 -m venv venv
$ source venv/bin/activate or

(Windows)
# virtualenv venv
# venv/Scripts/activate
```

2. Install the requirements:

```
$ pip install -r requirements.txt
```

4. Scripts
### azure_auth_scale

This script has the definition of a class which contains methods to automate the creaton of azure groups, register and configure web apps, randomly assign groups to members, modify the redirect urls of the web apps and delete permanently the apps.

### azure_auth_scale_calls

This script is used to call the five main functions you will need, also it has an example of how to use the class defined in the azure_auth_scale script with each method.

5. Running the script
### azure_auth_scale_calls
At the end of this script you will find a class instantiation calling five functions, just uncomment the functions you want to run and read the documentation of each function. Make sure that you are located in the directory before executing the script.
### Example
azure_automation> python azure_auth_scale_calls.py
