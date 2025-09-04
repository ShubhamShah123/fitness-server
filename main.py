from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime
from collections import defaultdict
# from meals import MealsData
import os
import pyrebase
import hashlib
import pandas as pd
import numpy as np
import json

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

def organize_weekly_progress(progress_data, flag=None):
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

	if not flag:
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
	else:
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
				'weight_readings': weight_list,
				'average_weight': avg_weight,
				}
			
			formatted_weeks.append(week_data)
		
		return formatted_weeks
# --------------------- ROUTES ----------------------------

@app.route('/')
def index():
	print("Hello World")
	return jsonify({'date': datetime.now(), 'msg': 'hello world'}), 200

# Firestore data adding.
# @app.route('/add_data')
# def add_data():
# 	data = pd.read_csv('./datasets/schedule.csv')
# 	print(data)
# 	print("Dict:")
# 	data['day'] = data['day'].str.lower()
# 	to_add_data = data.set_index('day').to_dict(orient='index')
# 	for day in to_add_data:
# 		to_add_data[day]['exercise_key'] = ''
# 	res = db.child('dataset').child('schedule').set(to_add_data)
# 	if res:
# 		return jsonify({'status':'data added'}), 200
# 	else:
# 		return jsonify({'status': 'Some error happened pushing data.'}), 400

# @app.route('/add_exercise')
# def add_exercise():
# 	print("---- adding exercise ----")
# 	# days = ['monday','tuesday','wednesday','thursday','friday','saturday']
# 	days = ['wednesday']
# 	for day in days:
# 		df = pd.read_csv(f'./datasets/{day}.csv', dtype={'id': str})
# 		print(f"[+] Reading {day}.csv ...")
# 		df['id'] = df['id'].astype(str)
# 		to_add_data = df.set_index('id').to_dict(orient='index')
# 		print(to_add_data)

# 		# Replace NaN with None and make sure everything is JSON serializable
# 		for outer_k, inner_dict in to_add_data.items():
# 			for inner_k, v in inner_dict.items():
# 				if pd.isna(v):  # catches np.nan, None, NaT
# 					inner_dict[inner_k] = None
# 		json.dumps(to_add_data)
# 		res = db.child('dataset').child('exercise').push(to_add_data)
# 		sch = db.child('dataset').child('schedule').child(day).update({'exercise_key': res['name']})
# 	return jsonify({"status": "data added and key updated."}), 200

# @app.route('/add_meals')
# def add_meals():
# 	print("--- adding meals ---")
	
# 	for meal in MealsData:
# 		meal_id = meal['id']

# 		# First store the main meal data (day & type)
# 		db.child('dataset').child('meals').child(str(meal_id)).set({
# 			'day': meal['day'],
# 			'type': meal['type']
# 		})

# 		# Then store each detail item as its own node
# 		for detail in meal['details']:
# 			meal_num = detail['meal_num']

# 			# Store detail under "details/{meal_num}"
# 			db.child('dataset').child('meals').child(str(meal_id)).child('details').child(meal_num).set({
# 				'meal_type': detail['meal_type'],
# 				'meal_name': detail['meal_name'],
# 				'recipe': detail['recipe']
# 			})

# 	return jsonify({'status': 'Meals and details added to DB'}), 200

@app.route('/get_meals_schedule', methods=['GET'])
def get_meals_schedule():
	print("--- get meals schedule ---")
	meals = db.child('dataset').child('meals').get().val()
	# Remove None from details lists
	to_send_list = []
	for meal_id, meal in enumerate(meals[1:]):
		meal['details'][:] = [d for d in meal['details'] if d is not None]
		to_send_dict = {
			'id':meal_id+1,
			'day': meal['day'],
			'type': meal['type'],
			'num_meals': len(meal['details'])
		}
		to_send_list.append(to_send_dict)
	return jsonify({'status': 'Successfull!','data': to_send_list}), 200

@app.route('/get_meal_data/<id>', methods=['GET'])
def get_meal_data(id):
	print(f"--- Getting Meals data for ID: {id} | {type(id)}---")
	meal_data = db.child('dataset').child('meals').child(id).get().val()
	print(meal_data)
	meal_data['details'][:] = [d for d in meal_data['details'] if d is not None]
	print(meal_data)
	return jsonify({'status':'Got the data!','data':meal_data}), 200
#----------------------------------------------------------

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
				return jsonify({'msg': 'Succesfully Logged in !', 'key': key, 'status_code': 200, 'flag': flag}), 200
			else:
				return jsonify({'msg': 'Password Incorrect', 'key': None, 'status_code': 401}), 401
		
	return jsonify({'msg': 'User not found', 'key': None, 'status_code': 404})	, 404

@app.route('/get_workout_schedule_v2', methods=['GET'])
def get_workout_schedule_v2():
	print("# ---- get_workout_schedule_v2 ----")
	sched = db.child('dataset').child('schedule').get()
	vals = sched.val()

	sending_list = []
	for key in vals:
		sending_dict = {
			"day": key,
			"exercise": vals[key]['exercise'],
			"id": vals[key]['id'],
			"key": vals[key]['exercise_key']
		}
		sending_list.append(sending_dict)

	# Custom day order
	day_order = [
		"monday", "tuesday", "wednesday", "thursday",
		"friday", "saturday", "sunday"
	]

	# Sort by custom order
	sending_list.sort(key=lambda x: day_order.index(x["day"].lower()))
	print("Sending List: \n", sending_list)
	return jsonify({'status_code': 200, 'data': sending_list}), 200


@app.route('/get_workout_details_v2/<id>', methods=['GET'])
def get_workout_details_v2(id):
	print("# ---- get_workout_details_v2 ----")
	print("Request from client: ", id)

	exercise_data = db.child('dataset').child('exercise').child(id).get().val()
	print("Raw data from DB:", exercise_data)

	sending_list = []
	if exercise_data:   # ✅ only loop if data exists
		for key in exercise_data:
			print("Key:", key)
			if 'desc' not in exercise_data[key]:
				exercise_data[key]['desc'] = ''
			sending_dict = {
				'id': key,
				'details': exercise_data[key]
			}
			sending_list.append(sending_dict)
	else:
		print("⚠️ No data found for:", id)

	return jsonify({
		'status': 'Working',
		'data': sending_list   # will be [] if no exercises (like Sunday)
	})


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
	to_send_list = []
	print(histDetail.val())
	if histDetail:
		to_send_list.append(histDetail.val())
		return jsonify({'data': to_send_list, 'status_code': 200}), 200
	return jsonify({'msg': 'No data available', 'status_code': 204}), 204

@app.route('/upload_session', methods=['POST'])
def upload_session():
	print("--- upload session ---")
	data = request.get_json()
	print("Data from the client:\n",data)
	# return jsonify({'status':'still working'}), 200
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
		exKey = data['day']
		print("exercise key: ",exKey)
		nameData = db.child('dataset').child('schedule').get().val()
		
		exercise_name = next((day_info['exercise'] for day_info in nameData.values() if day_info['exercise_key'] == exKey),None)
		print(f"Exercise Name: {exercise_name}| Key: {exKey}")
		data['day'] = exercise_name
		# return jsonify({'status':'still working'}), 200
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
				cnt = db.child('streak').get().val()
				print("Streak: ",cnt)
				return jsonify({'msg': 'Data added to sesssion & streak updated.', 'status_code': 200, 'key': histDataResp['name']}), 200
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

@app.route('/get_recent_workouts', methods=['GET'])
def get_recent_workouts():
	to_send_list=[]
	recent_workouts = db.child('session').order_by_key().limit_to_last(7).get()
	
	for workout in recent_workouts.each():
		data = workout.val()
		filtered = {
			'date': data['date'],
			'day': data['day'],
			'sessionTime': data['sessionTime'],
			'name':'name' # Add the name later on. Need to send the name of exercise as well.
		}
		to_send_list.append(filtered)
	return jsonify({'msg': 'Recent Workouts List.', 'status_code': 200, 'data': to_send_list}), 200

@app.route('/get_weights', methods=['GET'])
def get_weights():
	print("--- get weights ---")
	try:
		weights_df = db.child('history').get()
		monthly_data = defaultdict(list)

		for w in weights_df.each():
			data = w.val()
			date_str = data.get('date', '')
			weight_str = data.get('weight', '')
			print(f"Date: {date_str}")
			print(f"Weight: {weight_str}")
			print("----------------")
			# Skip if weight is empty
			if not weight_str:
				continue

			try:
				# Parse the date (e.g., "Feb 03, 2025")
				dt = datetime.strptime(date_str, "%b %d, %Y")
				month_key = dt.strftime("%Y-%m")  # "2025-02"

				# Convert weight to float
				weight = float(weight_str)

				# Group by month
				monthly_data[month_key].append(weight)
			except Exception as e:
				print(f"Skipping invalid entry: {data} | Error: {e}")

		# Compute average weights
		monthly_avg = []
		for month, weights in monthly_data.items():
			avg = round(sum(weights) / len(weights), 2)
			monthly_avg.append({
				"month": month,
				"averageWeight": avg
			})

		# Optional: sort by month
		monthly_avg.sort(key=lambda x: x["month"])
		print("[+] Organizign the data to weekly...")
		weekly_df = organize_weekly_progress(weights_df,flag=1)
		print(weekly_df)
		
		return jsonify({
			'status': 'success',
			'monthly': monthly_avg,
			'weekly':weekly_df
		}), 200

	except Exception as e:
		return jsonify({
			'status': 'error',
			'message': str(e)
		}), 500

@app.route('/get_workout_day',methods=['GET'])
def get_workout_day():
	print("---- GET WORKOUT DAY ----")
	date = datetime.today().strftime("%A")
	sch_df = db.child('dataset').child('schedule').get()

	exercise_name = sch_df.val()[date.lower()]['exercise']
	exercise_key = sch_df.val()[date.lower()]['exercise_key']
	exercise_data = db.child('dataset').child('exercise').child(exercise_key).get().val()
	print("exercise data\n",exercise_data)
	to_send_dict = {
		'name':exercise_name,
		'exercise_list':list(exercise_data.values())[1:]
	}
	return jsonify({'status_code':200,'data':to_send_dict}), 200

@app.route('/update_exercise/<id>',methods=['PATCH'])
def update_exercise(id):
	data = request.get_json()
	print("----- updating exercise -----")
	print("Data: ", data)
	to_update_date = {
		'desc':data['desc'],
		'sets':data['sets'],
		'reps':data['reps']
	}
	updated_ref = db.child('dataset').child('exercise').child(data['day']).child(data['id']).update(to_update_date)

	if updated_ref:
		print(updated_ref)
		return jsonify({'status':'Updated the data'}), 200
	else:
		return jsonify({'status': 'Updation Failed.'}), 400


@app.route('/add_new_exercise/<id>', methods=['POST'])
def add_new_exercise(id):
	print("--- Adding new Exercise ---")
	print("Request ID: ", id)
	data = request.get_json()
	print(f"Data from the client:\n{data}")
	exId = data['id']
	exData = {k: v for k, v in data.items() if k != "id"}
	newEx = db.child('dataset').child('exercise').child(id).child(exId).set(exData)
	if newEx:
		print(f"Data successfully added! {newEx}")
		return jsonify({'status': 'Data added succesfully', 'key':exId}), 200
	else:
		print(f"Data addition failed!")
		return jsonify({'status': 'Data addition failed.', 'key':None}), 400
	

@app.route('/get_streak_counter', methods=['GET'])
def get_streak_counter():
	print("--- get streak counter ---")
	cnt = db.child('streak').get().val()
	print("Streak: ",cnt, type(cnt))
	return jsonify({'status': 'Still working', 'counter':str(cnt)}),200

@app.route('/get_profile', methods=['POST'])
def get_profile():
	print("--- Getting Profile ---")
	data = request.get_json()
	userKey = data['key']
	print("UserKey from the client: ", userKey)
	userProfile = db.child('users').child(userKey).get().val()
	print(userProfile)
	to_send_dict = {
		'firstName': userProfile['firstName'],
		'lastName': userProfile['lastName'],
		'email': userProfile['email'],
		'phoneNumber': userProfile['phoneNumber']
	}
	
	return jsonify({'status': 'Getting the profile', 'data':to_send_dict}), 200

@app.route('/get_daily_workouts',methods=['GET'])
def get_daily_workouts():
	print("---- get daily workouts ----")
	
	try:
		# Step 1: Batch fetch all required data
		histData = db.child('history').get()
		all_sessions = db.child('session').get()
		schedule_data = db.child('dataset').child('schedule').get()
		
		# Step 2: Create lookup dictionaries for O(1) access
		sessions_dict = {}
		if all_sessions:
			for session in all_sessions.each():
				sessions_dict[session.key()] = session.val()
		
		schedule_dict = {}
		if schedule_data:
			for day_data in schedule_data.each():
				schedule_dict[day_data.key()] = day_data.val()['exercise']
		
		to_send_list = []
		processed_session_ids = set()  # Track which sessions we've processed
		
		# Step 3: Process history data (existing logic but with lookups)
		if histData:
			for hist in histData.each():
				session_id = hist.val()['sessionId']
				processed_session_ids.add(session_id)
				
				# Use dictionary lookup instead of database call
				session_data = sessions_dict.get(session_id)
				if session_data:
					day_lower = session_data['day'].lower()
					exercise_name = schedule_dict.get(day_lower, 'Unknown Exercise')
					
					to_send_list.append({
						'histKey': hist.key(),
						'date': hist.val()['date'],
						'sessKey': session_id,
						'sessDay': session_data['day'],
						'sessName': exercise_name
					})
		
		# Step 4: Process sessions that don't have history records
		for session_key, session_data in sessions_dict.items():
			if session_key not in processed_session_ids:
				day_lower = session_data['day'].lower()
				exercise_name = schedule_dict.get(day_lower, 'Unknown Exercise')
				
				to_send_list.append({
					'histKey': None,  # No history record exists
					'date': session_data.get('date', None),  # Use session date if available
					'sessKey': session_key,
					'sessDay': session_data['day'],
					'sessName': exercise_name
				})
		
		return jsonify({'status': 'Got the data.', 'data': to_send_list}), 200
		
	except Exception as e:
		print(f"Error in get_daily_workouts: {str(e)}")
		return jsonify({'status': 'Failed', 'data': []}), 400


@app.route('/get_daily_workout_report', methods=['POST'])
def get_daily_workout_report():
	print("--- /get_daily_workout_report ---")
	data = request.get_json()
	hKey = data['histKey']
	sKey = data['sessKey']
	print(f"history: {hKey} | session: {sKey}")
	
	histData = db.child('history').child(hKey).get().val()
	sessData = db.child('session').child(sKey).get().val()
	print(f"---- HISTORY ----\n{histData}\n---- SESSION ----\n{sessData}")
	
	# Extract meals data from history (excluding sessionId and date)
	meals_data = {
		'breakfast': histData.get('breakfast', ''),
		'lunch': histData.get('lunch', ''),
		'dinner': histData.get('dinner', ''),
		'preWorkout': histData.get('preWorkout', ''),
		'snack': histData.get('snack', ''),
		'workout': histData.get('workout', ''),
		'weight': histData.get('weight', ''),
		'hip': histData.get('hip', ''),
		'stomach': histData.get('stomach', ''),
		'thigh': histData.get('thigh', ''),
		'waist': histData.get('waist', '')
	}
	exData = db.child('dataset').child('schedule').child(sessData.get('day', '').lower()).get()
	# Extract session data (excluding date)
	session_data = {
		'day': sessData.get('day', ''),
		'name': exData.val()['exercise'],
		'exercise': sessData.get('exercise', {}),
		'sessionTime': sessData.get('sessionTime', ''),
		'totalTimeTaken': sessData.get('totalTimeTaken', '')
	}
	
	# Create combined response
	response_data = {
		'meals': meals_data,
		'session': session_data,
		'date': histData.get('date', '')  # Keep one date reference
	}
	
	return jsonify({'status':'Completed!','data':response_data}), 200
'''
TODO: 
Checkout the upload session part. The exercise is undefined and the key of the exercise is going in name.
'''

if __name__ == '__main__':
	port = int(os.environ.get('PORT', 8080))
	# CHANGE THIS TO 0.0.0.0 WHILE PUBLISHING ON HEROKU
	app.run(host='0.0.0.0', port=port, debug=True)
	# app.run(host='10.236.36.36', port=port, debug=True)
