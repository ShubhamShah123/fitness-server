from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime, date
from collections import defaultdict
import re
import os
import pyrebase
import hashlib

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
def get_average_time(timeTakenList):
	total_minutes = 0

	for t in timeTakenList:
		h, m = t.replace('h', '').replace('m', '').split()
		total_minutes += int(h) * 60 + int(m)

	average_minutes = total_minutes / len(timeTakenList)

	avg_hours = int(average_minutes // 60)
	avg_minutes = int(average_minutes % 60)

	average_time = f"{avg_hours}h {avg_minutes}m"
	return average_time


def get_week_number(date_str):
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
	meal_data['details'][:] = [d for d in meal_data['details'] if d is not None]
	return jsonify({'status':'Got the data!','data':meal_data}), 200


@app.route('/upload_schedule', methods=['POST'])
def upload_schedule():
	data = request.get_json()
	print(data)
	res = db.child('dataset').child('schedule').child('profile1').set(data)
	if res:
		return jsonify({'status': 'If res','return': res}), 200
	else:
		return jsonify({'status': 'Else','return': 'Error'}), 400

@app.route('/upload_exercise', methods=['POST'])
def upload_exercise():
	data = request.get_json()

	exData = db.child('dataset').child('exercise').push(data)
	if not exData:
		return jsonify({'status': 'Error pushing exercise'}), 400

	exKey = exData['name']
	week_list = []
	for i in range(1, 13):
		week_key = f"week{i}"
		ref = db.child('dataset').child('schedule').child('profile1')
		week_data = ref.child(week_key).get()
		result = week_data.val()
		for day, day_data in result.items():
			if day_data['name'] == data['name']:
				week_list.append((week_key,day))
	print(f"Week List: {week_list}")
	for week, day in week_list:
		print(week, day, exKey)
		db.child('dataset').child('schedule').child('profile1').child(week).child(day).update({'exKey': exKey})
	return jsonify({'status': 'Still Working'}),200
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

@app.route('/get_workout_schedule/<profile>', methods=['GET'])
def get_workout_schedule(profile):
	print("# ---- get_workout_schedule ----")

	sched = db.child('dataset').child('schedule').child(profile).get()
	vals = sched.val()
	days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
	days_dict = {day: i for i, day in enumerate(days, 1)}
	for week_key in vals:
		week = vals[week_key]
		week_numbered = {days_dict[day]: data for day, data in week.items()}
		vals[week_key] = dict(sorted(week_numbered.items()))
	to_send_list = []
	to_send_dict = {}
	for k, v in vals.items():
		new_k = int(k.replace("week", ""))
		to_send_dict[new_k] = v
	
	return jsonify({'status': 'Still Working', 'code': 200, 'data':to_send_dict}), 200

	
@app.route('/get_workout_details/<id>', methods=['GET'])
def get_workout_details(id):
	print("# ---- get_workout_details ----")
	workout_data = db.child('dataset').child('exercise').child(id).get().val()
	if workout_data:
		return jsonify({'status_code': 200, 'data': workout_data, 'msg': 'Successfully got the exercise data'}), 200
	else:
		return jsonify({'status_code': 400, 'data': '', 'msg': 'Error getting the exercise data'}), 400

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
	print(f"Date from client: \n{data}")
	# return jsonify({'status':'Still Working'}), 501
	date_str = data['date'] # This goes to session
	exKey = data['day']
	nameData = db.child('dataset').child('schedule').get().val()
	print(1)
	# day_of_week = next((day for day, day_info in nameData.items() if day_info['exercise_key'] == exKey), None)
	day_of_week = data['day_of_week'].lower()
	print(2)
	data['day'] = day_of_week
	print(3)
	date_obj = datetime.strptime(date_str, "%Y-%m-%d")
	
	print(4)
	formatted_date = date_obj.strftime("%b %d, %Y") # This goes to History
	sessTime = data['sessionTime']
	print(5)
	if sessTime.lower() == 'evening':
		print(6)
		sessData = db.child('session').push(data)
		if sessData:
			req_date_data = db.child('history').order_by_child('date').equal_to(formatted_date).get()
			for req in req_date_data.each():
				db.child('history').child(req.key()).update({'sessionId': sessData['name']})
			return jsonify({'msg': 'Updated the session key!', 'status_code': 200}), 200

	elif sessTime.lower() == 'morning':
		print(7)
		prevData = db.child('session').order_by_key().limit_to_last(1).get().val()
		if prevData:  # Check if prevData is not empty
			prev_date = [val['date'] for _, val in prevData.items()][0]
			date_str = data['date']  # This goes to session
			date_diff = date.fromisoformat(date_str) - date.fromisoformat(prev_date)
			days_diff = date_diff.days
		else:
			days_diff = 0
		sessData = db.child('session').push(data)
		if sessData:
			sessionKey = sessData['name']
			histData = {
				"breakfast": 'missed', 
				"date": formatted_date, 
				"dinner": 'missed',
				"hip": '',
				"lunch": 'missed',
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
				new_streak = 0
				if days_diff == 1:
					new_streak = int(cnt) + 1
					db.child('streak').set(new_streak)
				else:
					db.child('streak').set(1)
				return jsonify({'msg': 'Data added to sesssion & streak updated.', 'status_code': 200, 'key': histDataResp['name'], 'new_streak': str(new_streak)}), 200
			else:
				return jsonify({'msg': 'Failed to add History data.', 'status_code': 400, 'key': None}), 400
		else:
			return jsonify({'msg': 'Error.', 'status_code': 400, 'key': None}), 400

@app.route('/delete_workout', methods=['DELETE'])
def delete_workout():
	print("---- deleting workout ---- ")
	data = request.get_json()
	print(data)
	keyList = data['keyList']
	for i, v in enumerate(keyList):
		print(f"{i}: {v}")
		try:
			db.child('history').child(v['histKey']).remove()
			db.child('session').child(v['sessKey']).remove()
		except Exception as e:
			print(f"Error while deleting: {e}")
	return jsonify({'msg': 'Successfully deleted', 'status_code': 200}), 200

@app.route('/get_session_progress', methods = ['POST'])
def get_session_progress():
	data = request.get_json()
	query_date = data['query_date']
	print(data)
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
	print(f"--- Data for: {query_date} ---\n{to_send_data}")
	return jsonify({'msg': 'Still Working', 'status_code': 200, 'data': to_send_data}), 200

@app.route('/update_session_progress', methods=['PUT'])
def update_session_progress():
	print("---- update sesssion progress ---")
	data = request.get_json()
	req_date = data['date']
	print(f"Req Date: {req_date}")
	sessData = db.child('history').order_by_child('date').equal_to(req_date).get()
	print(sessData.val())
	if sessData.val():
		sKey = None
		for sItem in sessData.each():
			sKey = sItem.key()
		result = db.child('history').child(sKey).update(data)
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
	print("---- get recent workouts ----")
	recent_workouts = db.child('session').order_by_key().limit_to_last(7).get()
	print(recent_workouts.val())
	for workout in recent_workouts.each():
		data = workout.val()
		filtered = {
			'date': data['date'],
			'day': data['day'].capitalize(),
			'sessionTime': data['sessionTime'].capitalize(),
			'name':data['workoutName'] # Add the name later on. Need to send the name of exercise as well.
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
		weekly_df = organize_weekly_progress(weights_df,flag=1)
		# print(weekly_df)
		
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
	date = datetime.today().strftime("%A").lower()
	print("Date: ", date)
	workout_name = db.child('dataset').child('schedule').child('profile1').child('week1').child(date).get().val()
	workout_detail = db.child('dataset').child('exercise').child(workout_name['exKey']).get().val()
	exercise_list = [v for k, v in workout_detail['details'].items()]
	print(workout_detail['details'])
	to_send_dict = {
		'name': workout_name['name'],
		'exercise_list': exercise_list
	}
	return jsonify({'status': 'Still Working','data': to_send_dict}), 501

@app.route('/update_exercise/<id>',methods=['PATCH'])
def update_exercise(id):
	data = request.get_json()
	print("----- updating exercise -----")
	print(data)
	to_update_date = {
		'desc':data['desc'],
		'sets':data['sets'],
		'reps':data['reps']
	}
	updated_ref = db.child('dataset').child('exercise').child(data['day']).child('details').child(data['id']).update(to_update_date)

	if updated_ref:
		print(updated_ref)
		return jsonify({'status':'Updated the data'}), 200
	else:
		return jsonify({'status': 'Updation Failed.'}), 400


@app.route('/add_new_exercise/<id>', methods=['POST'])
def add_new_exercise(id):
	print("--- Adding new Exercise ---")
	data = request.get_json()
	exId = data['id']
	exData = {k: v for k, v in data.items() if k != "id"}
	newEx = db.child('dataset').child('exercise').child(id).child(exId).set(exData)
	if newEx:
		return jsonify({'status': 'Data added succesfully', 'key':exId}), 200
	else:
		return jsonify({'status': 'Data addition failed.', 'key':None}), 400
	

@app.route('/get_streak_counter', methods=['GET'])
def get_streak_counter():
	print("--- get streak counter ---")
	cnt = db.child('streak').get().val()
	return jsonify({'status': 'Still working', 'counter':str(cnt)}),200

@app.route('/get_profile/<userKey>', methods=['GET'])
def get_profile(userKey):
	print("--- Getting Profile ---")
	userProfile = db.child('users').child(userKey).get().val()
	sessionData = db.child('session').get()
	sessionCount = len(sessionData.val()) if sessionData else 0
	timeTakenList = [k.val()['totalTimeTaken'] for k in sessionData.each()]
	averageTimeSession = get_average_time(timeTakenList)
	to_send_dict = {
		'firstName': userProfile['firstName'],
		'lastName': userProfile['lastName'],
		'email': userProfile['email'],
		'phoneNumber': userProfile['phoneNumber'],
		'sessionCount': sessionCount,
		'averageTimeSession': averageTimeSession
	}
	
	return jsonify({'status': 'Getting the profile', 'data':to_send_dict}), 200

@app.route('/get_daily_workouts',methods=['GET'])
def get_daily_workouts():
	print("---- get daily workouts ----")
	historyData = db.child('history').get().val()
	to_send_list = []
	for k, v in historyData.items():
		sessionData = db.child('session').child(v['sessionId']).get().val()
		to_send_dict = {
			'histKey': k,
			'sessKey': v['sessionId'],
			'date': v['date'],
			'sessDay': sessionData['day_of_week'],
			'sessName': sessionData['workoutName']
		}
		to_send_list.append(to_send_dict)
	return jsonify({'status_code': 200,'data': to_send_list}), 200
	


@app.route('/get_daily_workout_report', methods=['POST'])
def get_daily_workout_report():
	print("--- /get_daily_workout_report ---")
	data = request.get_json()
	hKey = data['histKey']
	sKey = data['sessKey']
	
	histData = db.child('history').child(hKey).get().val()
	sessData = db.child('session').child(sKey).get().val()
	
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
		'day': sessData.get('day', '').capitalize(),
		'name': sessData.get('workoutName', ''),
		'exercise': sessData.get('exercise', {}),
		'sessionTime': sessData.get('sessionTime', ''),
		'totalTimeTaken': sessData.get('totalTimeTaken', ''),
		'weekNumber': sessData.get('weekNumber', '')
	}
	
	# Create combined response
	response_data = {
		'meals': meals_data,
		'session': session_data,
		'date': histData.get('date', '')  # Keep one date reference
	}
	
	return jsonify({'status':'Completed!','data':response_data}), 200

@app.route('/delete_sched_workout', methods=['DELETE'])
def delete_sched_workout():
	print("--- delete_sched_workout ---")
	data = request.get_json()
	db.child('dataset').child('exercise').child(data['sId']).child(data['exId']).remove()
	return jsonify({'status': 'Successfully Deleted!','status_code': 200}), 200

@app.route('/get_exercise_list', methods=['GET'])
def get_exercise_list():
	print("--- get_exercise_list ---")
	exData = db.child('dataset').child('exercise').get().val()
	to_send_list = []
	for key, value in exData.items():
		exDetails = value.get('details')
		if exDetails:
			for k, v in exDetails.items():
				gif_name = v['exName'].lower()
				if '-' in gif_name: gif_name = gif_name.replace(' - ','_')
				else: gif_name = gif_name.replace(' ','_')
				gif_name += '.gif'
				to_send_list.append({'name': v['exName'], 'gif': gif_name})
	return jsonify({'status': 'Got the list','status_code': 200, 'data': to_send_list}), 200

@app.route('/updating_keys/<id>', methods=['PATCH'])
def updating_keys(id):
	wData = db.child('dataset').child('exercise').child(id).child('details').get().val()
	update_dict = {}
	for i, v in enumerate(wData):
		print(i, v)
		update_dict[f'{i}A'] = v
	print(update_dict)
	db.child('dataset').child('exercise').child(id).child('details').set(update_dict)
	return jsonify({'status': 'Still Working'}), 501

if __name__ == '__main__':
	port = int(os.environ.get('PORT', 8080))
	app.run(host='0.0.0.0', port=port, debug=True)
	# app.run(host='11.49.175.179', port=port, debug=True)
