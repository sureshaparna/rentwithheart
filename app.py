from flask import Flask, render_template, redirect, url_for

app = Flask(__name__, template_folder='templates', static_folder='static')

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/suburb/<int:Number>')
def suburb_historicaldata(Number):
    if Number < 0 or Number > 7:
        return redirect(url_for('home'))
    else:
        if Number == 0:
            return render_template('suburb_forecast.html')
        return render_template('historical_trends/subdat'+str(Number)+'.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/procedure')
def procedure():
    return render_template('procedure.html')

@app.route('/recommender')
def recommender():
    return render_template('recommender.html')

@app.route('/support')
def support():
    return render_template('support.html')

if __name__ == '__main__':
    app.run(debug=True)
