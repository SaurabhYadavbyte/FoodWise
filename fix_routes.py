import re

with open('app/routes.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_feedback = """@app.route('/feedback', methods=['GET', 'POST'])
@login_required
def feedback():
    if request.method == 'POST':
        rating = request.form.get('rating')
        category = request.form.get('category')
        message = request.form.get('message', '').strip()
        
        if not rating or not category or not message:
            flash("All fields are required.", "danger")
            return redirect(url_for('feedback'))
            
        fb = Feedback(user_id=current_user.id, rating=int(rating), category=category, message=message)
        db.session.add(fb)
        db.session.commit()
        log_activity(current_user.id, 'Submitted Feedback', 'Feedback')
        flash('Thank you for your feedback.', 'success')
        return redirect(url_for('dashboard'))
        
    return render_template('feedback.html')"""

new_feedback = """@app.route('/feedback', methods=['GET', 'POST'])
@login_required
def feedback():
    if request.method == 'POST':
        rating_str = request.form.get('rating')
        category = request.form.get('category')
        message = request.form.get('message', '').strip()
        
        if not rating_str or not category or not message:
            flash("All fields are required.", "danger")
            return redirect(url_for('feedback'))
            
        try:
            rating = int(rating_str)
            if rating < 1 or rating > 5:
                raise ValueError()
        except ValueError:
            flash("Please select a valid rating.", "danger")
            return redirect(url_for('feedback'))
            
        allowed_categories = ['Suggestion', 'Bug', 'Usability', 'Feature Request', 'Other']
        if category not in allowed_categories:
            flash("Please select a valid category.", "danger")
            return redirect(url_for('feedback'))
            
        if len(message) > 2000:
            flash("Message is too long (max 2000 characters).", "danger")
            return redirect(url_for('feedback'))
            
        fb = Feedback(user_id=current_user.id, rating=rating, category=category, message=message)
        db.session.add(fb)
        db.session.commit()
        log_activity(current_user.id, 'Submitted Feedback', 'Feedback')
        flash('Thank you for your feedback.', 'success')
        return redirect(url_for('dashboard'))
        
    return render_template('feedback.html')"""

content = content.replace(old_feedback, new_feedback)

# Leftover wording update
old_leftover = """    elif insights['most_reason'] == "Leftover was not used":
        recommendation = "Check usable leftovers before preparing a new meal."
        priority_action = "Eat leftovers for your next meal.""""

new_leftover = """    elif insights['most_reason'] == "Leftover was not used":
        recommendation = "Check usable leftovers before preparing a new meal."
        priority_action = "Use safely stored leftovers in a suitable next meal.""""
        
content = content.replace(old_leftover, new_leftover)

with open('app/routes.py', 'w', encoding='utf-8') as f:
    f.write(content)
