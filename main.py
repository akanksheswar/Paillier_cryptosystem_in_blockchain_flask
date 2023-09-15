from flask import Flask, render_template, request, redirect, url_for, flash
import os
import pandas as pd
import mysql.connector
from phe import paillier
import hashlib
import time
from flask_wtf import FlaskForm
from wtforms import FileField, SubmitField
from flask_wtf.file import FileAllowed, FileRequired, DataRequired
import json

class UploadForm(FlaskForm):
    file = FileField('Upload File', validators=[DataRequired(message='Please select a file'), FileRequired(), FileAllowed(['csv'], 'CSV files only!')])
    submit = SubmitField('Submit')

class Block:
    def __init__(self, index, timestamp, data, previous_hash, nonce=0):
        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        data_string = str(self.index) + str(self.timestamp) + str(self.data) + str(self.previous_hash) + str(self.nonce)
        return hashlib.sha256(data_string.encode('utf-8')).hexdigest()

class Blockchain:
    def __init__(self):
        self.chain = [self.create_genesis_block()]

    def create_genesis_block(self):
        return Block(0, time.time(), "Genesis Block", "0")

    def get_last_block(self):
        return self.chain[-1]

    def add_block(self, new_block):
        new_block.previous_hash = self.get_last_block().hash
        new_block.hash = new_block.calculate_hash()
        self.chain.append(new_block)

    def is_valid_chain(self):
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i - 1]

            if current_block.hash != current_block.calculate_hash():
                return False

            if current_block.previous_hash != previous_block.hash:
                return False

        return True

    def mine_block(self, new_block):
        while True:
            if new_block.hash[:2] == "00":
                self.add_block(new_block)
                break
            else:
                new_block.nonce += 1
                new_block.hash = new_block.calculate_hash()

def blockchain_to_json(blockchain):
    json_blocks = []
    for block in blockchain.chain:
        json_block = {
            "index": block.index,
            "timestamp": block.timestamp,
            "data": block.data,
            "previous_hash": block.previous_hash,
            "nonce": block.nonce,
            "hash": block.hash
        }
        if isinstance(json_block["data"], dict) and "encrypted_percentage" in json_block["data"]:
            encrypted_percentage = json_block["data"]["encrypted_percentage"]
            if isinstance(encrypted_percentage, paillier.EncryptedNumber):
                json_block["data"]["encrypted_percentage"] = encrypted_percentage.ciphertext()
        json_blocks.append(json_block)
    return json_blocks

def all_employees_voted():
    query = "SELECT COUNT(*) FROM employee_details"
    mycusor.execute(query)
    total_employees = mycusor.fetchone()[0]
    
    query = "SELECT COUNT(*) FROM voting_details"
    mycusor.execute(query)
    voted_employees = mycusor.fetchone()[0]
    
    return total_employees == voted_employees

blockchain = Blockchain()

public_key, private_key = paillier.generate_paillier_keypair()

def encrypt_percentage(percentage):
    encrypted_per = public_key.encrypt(percentage)
    return encrypted_per

def decrypt_result(result):
    decrypted_result = private_key.decrypt(result)
    return decrypted_result

app = Flask(__name__, template_folder='template')

app.config["DEBUG"] = True
app.config['SECRET_KEY'] = '40359633'

UPLOAD_FOLDER = 'uploaded_files'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

mydb = mysql.connector.connect( 
    host="localhost", 
    user="root",
    password="",
    database="employees")

mycusor = mydb.cursor()

@app.route("/")
def home():
    try:
        form = UploadForm()
        if form.validate_on_submit():
            uploaded_file = form.file.data
            if uploaded_file.filename != '':
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], uploaded_file.filename)
                uploaded_file.save(file_path)
                parseCSV(file_path)
                flash('File uploaded successfully!', 'success')
            else:
                flash('No file selected.', 'danger')
        return render_template('home.html', form=form)
    except Exception as e:
        return render_template('error.html', error_message=str(e))

@app.route('/', methods = ['POST'])
def uploadfiles():
    uploaded_file = request.files['file']
    if uploaded_file.filename != '':
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], uploaded_file.filename)
        uploaded_file.save(file_path)
        parseCSV(file_path)
    return render_template('search.html')

def parseCSV(filePath):
    col_names = ['id', 'name', 'position']
    csvData = pd.read_csv(filePath, names=col_names, header=None)
    for i,row in csvData.iterrows():
        sql = "INSERT INTO employee_details (id,name,position) VALUES (%s,%s,%s)"
        value= (row['id'], row['name'], row['position'])
        mycusor.execute(sql,value)
        mydb.commit()

def search_user(search_input):
    query = "SELECT * FROM employee_details WHERE id = %s OR name LIKE %s"
    search_term = f'%{search_input}%'
    mycusor.execute(query, (search_input, search_term))
    results = mycusor.fetchall()
    return results

@app.route('/search', methods=['POST'])
def search():
    search_input = request.form['search_input']
    if not search_input:
        flash('Please enter a search term.', 'danger')
        return redirect(url_for('home'))
    search_results = search_user(search_input)
    employees_have_voted = all_employees_voted()
    return render_template('search.html', search_results=search_results, employees_have_voted=employees_have_voted)

@app.route('/vote', methods=['POST'])
def vote():
    try:
        id = int(request.form['id'])
        voting_percentage = int(request.form['voting_percentage'])
        if voting_percentage < 0 or voting_percentage > 100:
            raise ValueError("Voting percentage must be between 0 and 100")
        create_voting_details_table()
        insert_voting_data(id, voting_percentage)

        print(public_key)
        encrypted_percentage = encrypt_percentage(voting_percentage)
        print(encrypted_percentage)
        encrypted_vote_data = {
            "id": id,
            "encrypted_percentage": encrypted_percentage
        }

        new_block = Block(len(blockchain.chain), time.time(), encrypted_vote_data, blockchain.get_last_block().hash)
        blockchain.mine_block(new_block)
        
        print(decrypt_result(encrypted_percentage))
        return render_template('search.html')
    except ValueError as ve:
        return render_template('error.html', error_message=str(ve))
    except Exception as e:
        return render_template('error.html', error_message=str(e))

def create_voting_details_table():
    create_table_query = '''
    CREATE TABLE IF NOT EXISTS voting_details (
        id INT PRIMARY KEY,
        position VARCHAR(255),
        voting_percentage FLOAT
    )
    '''
    mycusor.execute(create_table_query)
    mydb.commit()

def insert_voting_data(id, voting_percentage):
    get_employee_query = "SELECT name, position FROM employee_details WHERE id = %s"
    mycusor.execute(get_employee_query, (id, ))
    employee_data = mycusor.fetchone()

    if employee_data:
        employee_name, employee_position = employee_data
        insert_query = '''
        INSERT INTO voting_details (id, position, voting_percentage)
        VALUES (%s, %s, %s)
        '''
        mycusor.execute(insert_query, (id, employee_position, voting_percentage))
        mydb.commit()

@app.route('/calculate', methods=['POST'])
def calculate():
    threshold = 15
    total_value = 45
    fetch_query = "SELECT voting_percentage FROM voting_details"
    mycusor.execute(fetch_query)
    voting_percentage_records = mycusor.fetchall()

    voting_percentage_record_arr = [record[0] for record in voting_percentage_records]
    print(voting_percentage_record_arr)
    
    encrypt_percentage_arr = []
    print(public_key)
    for record in voting_percentage_record_arr:
        a = encrypt_percentage(record)
        encrypt_percentage_arr.append(a)
    print(encrypt_percentage_arr)

    fetch_query1 = "SELECT position FROM voting_details"
    mycusor.execute(fetch_query1)
    position_records = mycusor.fetchall()

    position_dict = {
        "internship" : 1,
        "tester": 2,
        "developer" : 3,
        "team head" : 4,
        "manager" : 5,
        "director" : 6,
        "CIO" : 5,
        "vice president": 7,
        "CEO" : 8,
        "founder" : 9
    }

    position_records_arr = []
    for position_record in position_records:
        position = position_record[0]
        if position in position_dict:
            position_records_arr.append(position_dict[position])
        else:
            position_records_arr.append(0)
    
    final_resulth = 0
    for i in range(len(encrypt_percentage_arr)):
        final_resulth = final_resulth + ((encrypt_percentage_arr[i]) * (position_records_arr[i]))
    print(final_resulth)

    final_result_data = {
        "encrypted_result": final_resulth,
    }

    # new_block = Block(len(blockchain.chain), time.time(), final_result_data, blockchain.get_last_block().hash)
    # blockchain.mine_block(new_block)

    decrypt_result_value = decrypt_result(final_resulth)
    print(decrypt_result_value)

    if decrypt_result_value / 100 > (threshold / 100) * total_value:
        result_message = "Final result is more than the threshold percentage. Success"
    else:
        result_message = "Final result is less than to the threshold percentage. Not Success"

    return render_template('result.html', result_message=result_message)

    

@app.route('/blockchain', methods=['GET'])
def display_blockchain():
    return render_template('blockchain.html', blockchain=blockchain.chain)

@app.route('/export_blockchain', methods=['GET'])
def export_blockchain():
    json_blocks = blockchain_to_json(blockchain)
    
    with open('blockchain.json', 'w') as json_file:
        json.dump(json_blocks, json_file, indent=4)
    
    return "Blockchain data exported"


@app.errorhandler(404)
def page_not_found(error):
    return render_template('error.html', error_message="Page not found"), 404

@app.errorhandler(500)
def internal_server_error(error):
    return render_template('error.html', error_message="Internal server error"), 500

if (__name__ == "__main__"):
    app.run(port=5000, debug=True)

