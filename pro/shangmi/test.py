from flask import Flask,request

app = Flask(__name__)

@app.route("/test", methods=['GET', 'POST'])
def test():
	if request.method=="GET":
		params=request.args
		print(params)
		return 'ok'
	else:
		params = request.form
		print(params)
		return 'oko'

if __name__ == '__main__':
	app.run(
		host='0.0.0.0',
		port='12348',
		debug=True)