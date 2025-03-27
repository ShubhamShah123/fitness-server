from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime
from collections import defaultdict
import os
import pyrebase
import hashlib
import pandas as pd
import numpy as np

app = Flask(__name__)
CORS(app)

firebaseConfig = {
	"apiKey": "AIzaSyDwlHViwQSOeC95NeOji7ZdVW4HUHpoOqQ",
	"authDomain": "myfitness-8397.firebaseapp.com",
	"databaseURL": "https://myfitness-8397-default-rtdb.firebaseio.com",
	"projectId": "myfitness-8397",
	"storageBucket": "myfitness-8397.firebasestorage.app",
	"messagingSenderId": "268436627526",
	"appId": "1:268436627526:web:03e72f5878be0718fbaa47",
	"measurementId": "G-57FSKW11KZ"
}

firebase = pyrebase.initialize_app(firebaseConfig)
db = firebase.database()

# --------------------- FUNCTIONS ----------------------------

def get_week_number(date_str):
	"""Convert date string to week number relative to the first date in dataset"""
	date = datetime.strptime(date_str, '%b %d, %Y')
	day = date.day
	week_num = ((day - 1) // 7) + 1
	return date.isocalendar()[1]

def organize_weekly_progress(progress_data):
	"""Organize progress data into weekly chunks"""
	if not progress_data:
		return []
	
	# Convert the Firebase data into a list of dictionaries with proper dates
	entries = []
	for prog in progress_data.each():
		entry = prog.val()
		entry['id'] = prog.key()
		entries.append(entry)
	
	# Sort entries by date
	entries.sort(key=lambda x: datetime.strptime(x['date'], '%b %d, %Y'))
	# Group by week
	weekly_data = defaultdict(list)
	for entry in entries:
		week_num = get_week_number(entry['date'])
		weekly_data[week_num].append(entry)

	
	# Format the response
	formatted_weeks = []
	for week_num in sorted(weekly_data.keys()):
		# print("Week Num: ", week_num)
		week_entries = weekly_data[week_num]
		week_start = min(week_entries, key=lambda x: datetime.strptime(x['date'], '%b %d, %Y'))['date']
		week_end = max(week_entries, key=lambda x: datetime.strptime(x['date'], '%b %d, %Y'))['date']
		weight_list = [float(e.get('weight')) for e in week_entries if e.get('weight')]
		avg_weight = round(sum(weight_list) / len(weight_list), 2) if weight_list else 0.00
		
		week_data = {
			'week_number': week_num,
			'date_range': f"{week_start} to {week_end}",
			'entries': week_entries,
			'summary': {
				'total_entries': len(week_entries),
				'workouts_completed': sum(1 for e in week_entries if e.get('workout') == 'taken'),
				'meals_taken': {
					'breakfast': sum(1 for e in week_entries if e.get('breakfast') == 'taken'),
					'lunch': sum(1 for e in week_entries if e.get('lunch') == 'taken'),
					'dinner': sum(1 for e in week_entries if e.get('dinner') == 'taken'),
					'snack': sum(1 for e in week_entries if e.get('snack') == 'taken')
				},
				'weight_readings': weight_list,
				'average_weight': avg_weight
			}
		}
		formatted_weeks.append(week_data)
	
	return formatted_weeks
# --------------------- ROUTES ----------------------------

@app.route('/')
def index():
	print("Hello World")
	return jsonify({'date': datetime.now(), 'msg': 'Updated the server side and client side'}), 200

@app.route('/signup', methods=['POST'])
def signup():
	data = request.get_json()

	first_name = data["firstName"]
	last_name = data["lastName"]
	email = data["email"]
	password = data["password"]
	phoneNumber = data["phoneNumber"]
	role = data["role"]

	m = hashlib.md5()
	m.update(password.encode('utf-8'))
	hashed_password = m.hexdigest()
	print(f"pwd: {password} | hPwd: {hashed_password}")

	to_add_data = {
		"firstName": first_name,
		"lastName": last_name,
		"email": email,
		"password": hashed_password,
		"role": role,
		"phoneNumber" :phoneNumber
	}

	result = db.child('users').push(to_add_data)
	if result:
		return jsonify({'msg': 'Successfully Signed up.', 'key': result['name'], 'status_code': 200}), 200
	else:
		return jsonify({'msg': 'Error', 'key': None, 'status_code': 400}), 400


"""
	shahshubham845@gmail.com -> shubhamshah123
	shubhamshah8397@gmail.com -> shubham123
	admin@admin.com -> admin123
	user@user.com -> user1234
	client@client.com -> client12345
"""
@app.route('/login', methods=['POST'])
def login():
	print("---- login ----")
	data = request.get_json()
	email = data['email']
	password = data['password']
	m = hashlib.md5()
	m.update(password.encode('utf-8'))
	hashed_password = m.hexdigest()
	to_send_list = []
	usersData = db.child('users').get()
	for user in usersData.each():
		key = user.key()
		if email == user.val()['email']:
			if hashed_password == user.val()['password']:
				flag = 1 if user.val()['role'] == 'admin' else 0
				to_send_data = {
					'firstName': user.val()['firstName'],
					'lastName': user.val()['lastName'],
					'email': user.val()['email'],
					'phoneNumber': user.val()['phoneNumber']
				}
				to_send_list.append(to_send_data)
				return jsonify({'msg': 'Succesfully Logged in !', 'key': key, 'status_code': 200, 'flag': flag, 'data': to_send_list}), 200
			else:
				return jsonify({'msg': 'Password Incorrect', 'key': None, 'status_code': 401}), 401
		
	return jsonify({'msg': 'User not found', 'key': None, 'status_code': 404})	, 404

@app.route('/get_workout_schedule_v2', methods=['GET'])
def get_workout_schedule_v2():
	print("# ---- get_workout_schedule_v2 ----")
	schedDf = pd.read_csv('./datasets/schedule.csv')
	to_send_list = schedDf.to_dict(orient="records")
	return jsonify({'data': to_send_list, 'status_code': 200}), 200	

@app.route('/get_workout_details_v2', methods=['POST'])
def get_workout_details_v2():
	print("# ---- get_workout_details_v2 ----")
	day = request.get_json()['day'].lower()
	if day == 'sunday':
		return jsonify({'data': [1, "REST DAY", '', ''], 'status_code': 200}), 200	
	try:
		dayDf = pd.read_csv(f'./datasets/{day}.csv')
	except FileNotFoundError as e:
		return jsonify({'error': str(e), 'status_code': 404}), 404
	# end try
	dayDf['desc'].replace(np.nan, '', inplace=True)
	to_send_list = dayDf.to_dict(orient="records")
	return jsonify({'data': to_send_list, 'status_code': 200}), 200	

@app.route('/get_workout_schedule', methods=['GET'])
def get_workout_schedule():
	df = pd.read_csv("workout_schedule.csv")

	# Merge ABS and CARDIO into the main workout category for each day
	merged_workout = {}

	for _, row in df.iterrows():
		day = row['DAY']
		name = row['NAME']

		if day in merged_workout:
			if name not in merged_workout[day]:
				merged_workout[day].append(name)
		else:
			merged_workout[day] = [name]

	# Convert merged data to the desired format
	workout_data = [{"DAY": day, "NAME": " + ".join(names)} for day, names in merged_workout.items()]
	return jsonify({'workout_schedule': workout_data, 'status_code': 200}), 200

@app.route('/get_workout_details/<day>', methods=['GET'])
def get_workout_details(day):
	df = pd.read_csv("./workout_schedule.csv")
	df1 = df[df.DAY == day.upper()]
	name = df1['NAME'].unique().tolist()
	to_send_list = []
	for _, exer in df1.iterrows():
		to_send_dict = {
			'id': exer['ID'],
			'name': exer['EXERCISE'],
			'sets': exer['SETS'],
			'reps': exer['REPS']
		}
		to_send_list.append(to_send_dict)
	return jsonify({'data': to_send_list, 'status_code': 200, 'day': day, 'name': ' + '.join(name)}), 200

@app.route('/get_progress', methods=['GET'])
def get_progress():
	print("--- get progress ---")
	prog_data = db.child('history').get()
	
	if prog_data:
		weekly_progress = organize_weekly_progress(prog_data)
		return jsonify({
			'msg': 'Got the data',
			'status_code': 200,
			'weekly_data': weekly_progress
		}), 200
	else:
		return jsonify({
			'msg': 'No data found',
			'status_code': 204
		}), 204

@app.route('/get_history', methods=['GET'])
def get_history():
	histData = db.child('session').get()
	if histData:
		to_send_list = []
		for hist in histData.each():
			to_send_data = {
				'key': hist.key(),
				'histVal': hist.val()['date']
			}
			to_send_list.append(to_send_data)
		return jsonify({'msg': 'Got the history data.', 'data': to_send_list, 'status_code': 200}), 200
	else:
		return jsonify({'msg': 'Error.'}), 400

@app.route('/get_history_details/<id>', methods=['GET'])
def get_history_details(id):
	histDetail = db.child('session').child(id).get()
	day = histDetail.val()['day'].lower()
	df = pd.read_csv('./datasets/schedule.csv')
	exercise = df[df['day'].str.lower() == day.lower()]['exercise'].values
	to_send_list = []
	if histDetail:
		to_send_list.append(histDetail.val())
		to_send_list[0]['name'] = exercise[0]
		return jsonify({'data': to_send_list, 'status_code': 200}), 200
	return jsonify({'msg': 'No data available', 'status_code': 204}), 204

@app.route('/upload_session', methods=['POST'])
def upload_session():
	print("--- upload session ---")
	data = request.get_json()
	date_str = data['date'] # This goes to session
	date_obj = datetime.strptime(date_str, "%Y-%m-%d")
	formatted_date = date_obj.strftime("%b %d, %Y") # This goes to History
	sessTime = data['sessionTime']
	if sessTime.lower() == 'evening':
		sessData = db.child('session').push(data)
		if sessData:
			req_date_data = db.child('history').order_by_child('date').equal_to(formatted_date).get()
			for req in req_date_data.each():
				db.child('history').child(req.key()).update({'sessionId': sessData['name']})
			return jsonify({'msg': 'Updated the session key!', 'status_code': 200}), 200

	elif sessTime.lower() == 'morning':
		sessData = db.child('session').push(data)
		if sessData:
			sessionKey = sessData['name']
			histData = {
				"breakfast": 'missed', 
				"date": formatted_date, 
				"dinner": 'missed',
				"hip": '',
				"lunch": '',
				"preWorkout": 'missed',
				"sessionId": sessionKey,
				"snack": 'missed',
				"stomach": '',
				"thigh": '',
				"waist": '',
				"weight": '',
				"workout": 'missed'
			}
			histDataResp = db.child('history').push(histData)
			if histDataResp:
				return jsonify({'msg': 'Data added to sesssion.', 'status_code': 200, 'key': histDataResp['name']}), 200
			else:
				return jsonify({'msg': 'Failed to add History data.', 'status_code': 400, 'key': None}), 400
		else:
			return jsonify({'msg': 'Error.', 'status_code': 400, 'key': None}), 400

@app.route('/delete_workout/<key>', methods=['DELETE'])
def delete_workout(key):
	deleteHistKey = ''
	sessionData = db.child('session').child(key).get()
	if sessionData.val():
		histData = db.child('history').order_by_child("sessionId").equal_to(key).get()
		for hkey in histData.each():
			deleteHistKey = hkey.key()
	db.child('history').child(deleteHistKey).remove()
	db.child('session').child(key).remove()
	return jsonify({'msg': 'Successfully deleted', 'status_code': 200}), 200

@app.route('/get_session_progress', methods = ['POST'])
def get_session_progress():
	data = request.get_json()
	query_date = data['query_date']
	sessData = db.child('history').order_by_child('date').equal_to(query_date).get()
	sVal = None
	sKey = None
	for sItem in sessData.each():
		sVal = sItem.val()
		sKey = sItem.key()

	to_send_data = {
		'sKey': sKey,
		'sVal': sVal
	}

	return jsonify({'msg': 'Still Working', 'status_code': 200, 'data': to_send_data}), 200

@app.route('/update_session_progress', methods=['PUT'])
def update_session_progress():
	data = request.get_json()
	req_date = data['date']
	sessData = db.child('history').order_by_child('date').equal_to(req_date).get()
	if sessData.val():
		sVal = None
		sKey = None
		for sItem in sessData.each():
			sVal = sItem.val()
			sKey = sItem.key()

		to_send_data = {}
		for key in sVal.keys():
			to_send_data[key] = data[key]

		result = db.child('history').child(sKey).update(to_send_data)
		if result:
			return jsonify({'msg': 'Updated Successfully', 'status_code': 200}), 200
		else:
			return jsonify({'msg': 'Updation Failed', 'status_code': 500}), 500
	else:
		histData = db.child('history').push(data)
		if histData:
			return jsonify({'msg': f'Data pushed for {req_date}', 'status_code': 200, 'key': histData['name']}), 200

if __name__ == '__main__':
	port = int(os.environ.get('PORT', 8080))
	# CHANGE THIS TO 0.0.0.0 WHILE PUBLISHING ON HEROKU
	app.run(host='0.0.0.0', port=port, debug=True)
	# app.run(host='11.28.81.123', port=port, debug=True)
