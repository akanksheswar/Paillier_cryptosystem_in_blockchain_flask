Installing dependencies, configuring the database, and preparing the development environment are all part of setting up the environment for your Flask application with blockchain and Paillier encryption.
1.	 Set up Python:
Please verify the presence of Python on your system. The software can be obtained by downloading it from the official website at the following URL: https://www.python.org/downloads/
To check whether python was installed or not, go to the command prompt and type “python --version”.
2.	Setup Visual Studio:
The software can be obtained by accessing the official website at the following URL: https://code.visualstudio.com/.
Add python extension in the visual studio extensions marketplace.
3.	Create a Virtual Environment
The use of a virtual environment aids in the clean management of project dependencies. Open a terminal and type: to build a virtual environment.
‘python -m venv myenv’
Activate the virtual environment:
“myenv\Scripts\activate”
4.	Install Required Python Packages:
Navigate to your project directory within your virtual environment and install the essential Python packages with pip:
“pip install Flask flask-wtf pandas mysql-connector-python phe”
5.	Install and config MySQL:
Download the XAMPP control panel for connecting phpMyAdmin SQL. Make a MySQL database for your app (for example, "employees").
In your Flask application code, configure the database connection settings as below:
app.config["DEBUG"] = True
app.config['SECRET_KEY'] = '40359633'
UPLOAD_FOLDER = 'uploaded_files'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
mydb = mysql.connector.connect( 
host="localhost", 
user="root",
password="",
database="employees")
6.	Configure Paillier cryptosystem:
generate Paillier encryption keys (public_key and private_key). These keys are required for the encryption and decryption of voting percentages.
7.	Create HTML Templates:
Create HTML and CSS templates for your user interface and save them in the template’s directory.
