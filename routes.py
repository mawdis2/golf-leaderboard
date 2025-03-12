# routes.py
print("=== TESTING SIMPLE PATH ACCESS ===")
print("=== SECOND TEST - CONFIRMED FILE ACCESS ===")
from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash, get_flashed_messages, session
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy.sql import func, case, and_, or_
from datetime import datetime, timedelta
from models import db, User, Player, Birdie, Course, HistoricalTotal, Eagle, Tournament, Team, TeamMember, TournamentResult

print("TEST LINE WITH RELATIVE PATH - " + str(datetime.now()))

# Create a Blueprint
bp = Blueprint('main', __name__)

print("Routes file imported")

def clear_flash_messages():
    # Clear any existing flash messages
    get_flashed_messages(with_categories=True)

def check_site_auth():
    if not session.get('site_authenticated'):
        return redirect(url_for('main.site_password'))
    return None

@bp.route("/test")
def test():
    return "Test route is working!"

@bp.route("/")
def home():
    if not session.get('site_authenticated'):
        return redirect(url_for('main.site_password'))
    return redirect(url_for('main.leaderboard'))

@bp.route("/site_password", methods=['GET', 'POST'])
def site_password():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == 'shotgun':  # You can change this password
            session['site_authenticated'] = True
            session.permanent = True  # Make the session last longer
            return redirect(url_for('main.leaderboard'))
        else:
            flash('Incorrect password', 'error')
    return render_template('site_password.html')

@bp.route("/leaderboard")
def leaderboard():
    auth_check = check_site_auth()
    if auth_check:
        return auth_check
        
    current_year = datetime.now().year
    three_days_ago = datetime.now() - timedelta(days=3)
    players = Player.query.all()
    
    # First, calculate all scores and sort players
    player_scores = []
    for player in players:
        # Count regular birdies (not eagles)
        birdie_count = Birdie.query.filter(
            Birdie.player_id == player.id,
            Birdie.year == current_year,
            Birdie.is_eagle == False
        ).count()
        
        # Count eagles
        eagle_count = Birdie.query.filter(
            Birdie.player_id == player.id,
            Birdie.year == current_year,
            Birdie.is_eagle == True
        ).count()
        
        # Check for trophy
        has_trophy = HistoricalTotal.query.filter(
            HistoricalTotal.player_id == player.id,
            HistoricalTotal.year == current_year,
            HistoricalTotal.has_trophy == True
        ).first() is not None
        
        total = birdie_count + eagle_count
        player.birdie_count = birdie_count
        player.eagle_count = eagle_count
        player.total = total
        player.has_trophy = has_trophy
        
        # Initialize emojis string
        emojis = ""
        
        # Add trophy if player has one for current year
        if has_trophy:
            emojis += "🏆"
        
        # Check for recent birdies (within last 3 days)
        recent_birdies = Birdie.query.filter(
            Birdie.player_id == player.id,
            Birdie.is_eagle == False,
            Birdie.date >= three_days_ago,
            Birdie.year == current_year
        ).count()
        
        # Set recent_birdies on player object for template access
        player.recent_birdies = recent_birdies
        
        # Add one birdie emoji for each recent birdie
        if recent_birdies > 0:
            emojis += "🐤" * recent_birdies
            print(f"Found {recent_birdies} recent birdies for {player.name}")
            
        # Add eagle emojis for current year
        if eagle_count > 0:
            emojis += "🦅" * eagle_count
        
        player.emojis = emojis
        print(f"Final emojis for {player.name}: {emojis} (Recent birdies: {recent_birdies}, Eagles: {eagle_count}, Trophy: {has_trophy})")
        
        player_scores.append(player)
    
    # Sort players by total score (descending)
    player_scores.sort(key=lambda x: x.total, reverse=True)
    
    # Assign ranks with ties
    current_rank = 1
    prev_total = None
    players_at_rank = 0
    
    for i, player in enumerate(player_scores):
        if i == 0:
            # First player
            if len(player_scores) > 1 and player.total == player_scores[1].total:
                player.rank = f"T{current_rank}"
            else:
                player.rank = str(current_rank)
        else:
            if player.total == prev_total:
                player.rank = f"T{current_rank}"
            else:
                current_rank = i + 1
                if i < len(player_scores) - 1 and player.total == player_scores[i + 1].total:
                    player.rank = f"T{current_rank}"
                else:
                    player.rank = str(current_rank)
        
        prev_total = player.total
        print(f"{player.name}: Birdies={player.birdie_count}, Eagles={player.eagle_count}, Emojis={player.emojis}, Rank={player.rank}")
    
    return render_template("leaderboard.html", players=player_scores, year=current_year)

@bp.route("/add_player", methods=["GET", "POST"])
def add_player():
    auth_check = check_site_auth()
    if auth_check:
        return auth_check
        
    if request.method == "POST":
        name = request.form["name"].strip()
        existing_player = Player.query.filter(func.lower(Player.name) == func.lower(name)).first()
        if existing_player:
            flash("Player with this name already exists.", "error")
            return redirect(url_for("add_player"))
        new_player = Player(name=name)
        db.session.add(new_player)
        db.session.commit()
        flash("Player added successfully!", "success")
        return redirect(url_for("main.leaderboard"))
    clear_flash_messages()
    return render_template("add_player.html")

@bp.route("/add_birdie", methods=['GET', 'POST'])
def add_birdie():
    if request.method == 'POST':
        try:
            print("Form data received:")
            print(request.form)
            
            player_id = request.form.get('player_id')
            course_id = request.form.get('course_id')
            hole_number = request.form.get('hole_number')
            date_str = request.form.get('date')
            is_eagle_raw = request.form.get('is_eagle')
            
            # Parse and validate the date
            try:
                date = datetime.strptime(date_str, '%Y-%m-%d')
                current_year = datetime.now().year
                today = datetime.now().date()
                
                # Check if date is in current year and not in future
                if date.year != current_year:
                    flash('Please select a date from the current year.', 'error')
                    return redirect(url_for('main.add_birdie'))
                if date.date() > today:
                    flash('Cannot select a future date.', 'error')
                    return redirect(url_for('main.add_birdie'))
                    
            except ValueError:
                flash('Invalid date format.', 'error')
                return redirect(url_for('main.add_birdie'))
            
            print("is_eagle raw value:", is_eagle_raw)
            is_eagle = True if is_eagle_raw == 'true' else False
            print("is_eagle after conversion:", is_eagle)
            
            print("Received data:")
            print(f"Player ID: {player_id}")
            print(f"Course ID: {course_id}")
            print(f"Hole Number: {hole_number}")
            print(f"Date: {date_str}")
            print(f"Is Eagle: {is_eagle}")
            
            # Find the player
            player = Player.query.get(player_id)
            if player:
                print(f"Player found: {player.name}")
                
                # Create new birdie record
                new_record = Birdie(
                    player_id=player_id,
                    course_id=course_id,
                    hole_number=hole_number,
                    year=current_year,
                    date=date,
                    is_eagle=is_eagle
                )
                print(f"Created record: player={player.name}, is_eagle={is_eagle}")
                
                try:
                    db.session.add(new_record)
                    db.session.commit()
                    flash('Score added successfully!', 'success')
                except Exception as e:
                    db.session.rollback()
                    print(f"Error adding score: {e}")
                    flash('Error adding score. Please try again.', 'error')
            else:
                flash('Player not found.', 'error')
                
            return redirect(url_for('main.add_birdie'))
            
        except Exception as e:
            db.session.rollback()
            print(f"Error: {e}")
            flash('Error processing request. Please try again.', 'error')
            return redirect(url_for('main.add_birdie'))
    
    # For GET requests, just render the template
    try:
        players = Player.query.all()
        courses = Course.query.all()
        
        # Get date restrictions
        today = datetime.now().strftime('%Y-%m-%d')
        start_of_year = f"{datetime.now().year}-01-01"
        
        return render_template('add_birdie.html', 
            players=players, 
            courses=courses,
            min_date=start_of_year,
            max_date=today,
            current_year=datetime.now().year
        )
    except Exception as e:
        print(f"Error loading page: {e}")
        flash('Error loading page. Please try again.', 'error')
        return redirect(url_for('main.leaderboard'))

@bp.route("/add_course", methods=["GET", "POST"])
def add_course():
    if request.method == "POST":
        course_name = request.form.get("course_name")
        if course_name:
            try:
                course = Course(name=course_name)
                db.session.add(course)
                db.session.commit()
                flash(f'Course "{course_name}" added successfully!', 'success')
            except Exception as e:
                db.session.rollback()
                print(f"Error adding course: {e}")
                flash('Error adding course. Please try again.', 'error')
        else:
            flash('Course name is required.', 'error')
        return redirect(url_for('main.add_birdie'))
    return redirect(url_for('main.add_birdie'))

@bp.route("/players")
def get_players():
    players = Player.query.all()
    players_list = [player.to_dict() for player in players]
    return jsonify(players=players_list)

@bp.route("/player/<int:player_id>/records")
def player_birdie_records(player_id):
    player = Player.query.get_or_404(player_id)
    current_year = datetime.now().year
    
    # Get the selected year from the query parameter, default to current year
    selected_year = request.args.get('year', current_year, type=int)
    
    # Check if we're looking at historical data or current year
    if selected_year == current_year:
        # Get current year records from Birdie table
        records = db.session.query(
            Course.name.label('course_name'),
            Birdie.date,
            Birdie.hole_number,
            Birdie.is_eagle
        ).join(
            Course, Course.id == Birdie.course_id
        ).filter(
            Birdie.player_id == player_id,
            Birdie.year == selected_year
        ).order_by(
            Birdie.date.desc()
        ).all()
    else:
        # For historical years, check if we have individual records
        records = db.session.query(
            Course.name.label('course_name'),
            Birdie.date,
            Birdie.hole_number,
            Birdie.is_eagle
        ).join(
            Course, Course.id == Birdie.course_id
        ).filter(
            Birdie.player_id == player_id,
            Birdie.year == selected_year
        ).order_by(
            Birdie.date.desc()
        ).all()
        
        # If no individual records exist, get the summary from HistoricalTotal
        if not records:
            historical = HistoricalTotal.query.filter_by(
                player_id=player_id,
                year=selected_year
            ).first()
            
            if historical:
                # Create a summary message to display
                summary = {
                    'is_summary': True,
                    'birdies': historical.birdies,
                    'eagles': historical.eagles,
                    'has_trophy': historical.has_trophy
                }
                records = [summary]

    return render_template(
        "player_birdie_records.html",
        player=player,
        records=records,
        year=selected_year
    )

@bp.route("/player/<int:player_id>")
def player_details(player_id):
    player = Player.query.get_or_404(player_id)
    current_year = datetime.now().year
    
    # Get all birdies for the player for the current year
    birdies = Birdie.query.filter_by(
        player_id=player_id,
        year=current_year
    ).order_by(Birdie.date.desc()).all()
    
    # Count eagles
    eagle_count = sum(1 for birdie in birdies if birdie.is_eagle)
    
    return render_template(
        "player_details.html",
        player=player,
        birdies=birdies,
        eagle_count=eagle_count,
        year=current_year
    )

@bp.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user, remember=True)
            session['is_admin'] = True
            session.permanent = True
            flash('Logged in successfully.')
            return redirect(url_for('main.admin_dashboard'))
        else:
            flash('Invalid username or password')
    
    return render_template('login.html')

@bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.leaderboard'))

@bp.route("/admin")
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('You do not have permission to access the admin dashboard.')
        return redirect(url_for('main.leaderboard'))
    
    # Get all scores (both birdies and eagles) with eager loading of Course and Player
    scores = Birdie.query.options(
        db.joinedload(Birdie.course),
        db.joinedload(Birdie.player)
    ).order_by(Birdie.date.desc()).all()
    
    # Get all players
    players = Player.query.all()
    
    # Get all courses for the courses tab
    courses = Course.query.all()
    
    return render_template('admin_dashboard.html', 
                         scores=scores,
                         players=players,
                         courses=courses)

@bp.route("/admin/player_birdies", methods=["GET"])
def admin_player_birdies():
    if not session.get("is_admin"):
        flash("You do not have access to this page", "error")
        return redirect(url_for("login"))
    player_id = request.args.get("player_id")
    selected_player = Player.query.get_or_404(player_id)
    birdies = Birdie.query.filter_by(player_id=player_id).all()
    players = Player.query.all()
    courses = Course.query.all()
    return render_template("admin_dashboard.html", players=players, courses=courses, birdies=birdies, selected_player=selected_player)

@bp.route("/delete_player/<int:player_id>")
@login_required
def delete_player(player_id):
    # Check if user is logged in again
    if not current_user.is_authenticated:
        flash('Please log in to access this page')
        return redirect(url_for('login'))
    
    player = Player.query.get_or_404(player_id)
    
    # Delete all birdies for this player first
    Birdie.query.filter_by(player_id=player_id).delete()
    
    # Then delete the player
    db.session.delete(player)
    db.session.commit()
    
    flash(f'Player {player.name} has been deleted')
    return redirect(url_for('main.admin_dashboard'))

@bp.route("/delete_course/<int:course_id>")
@login_required
def delete_course(course_id):
    course = Course.query.get_or_404(course_id)
    
    # First delete all birdies associated with this course
    Birdie.query.filter(Birdie.course_id == course_id).delete()
    
    # Then delete the course
    db.session.delete(course)
    db.session.commit()
    
    flash(f'Course {course.name} has been deleted.')
    return redirect(url_for('main.admin_dashboard'))

@bp.route("/delete_birdie/<int:birdie_id>", methods=['POST'])
def delete_birdie(birdie_id):
    birdie = Birdie.query.get_or_404(birdie_id)
    player_id = birdie.player_id
    
    # If it's an eagle being deleted, update permanent_emojis
    if birdie.is_eagle:
        player = Player.query.get(player_id)
        if player.permanent_emojis and "🦅" in player.permanent_emojis:
            player.permanent_emojis = player.permanent_emojis.replace("🦅", "", 1)
            if not player.permanent_emojis.strip():  # If no emojis left
                player.permanent_emojis = None
    
    db.session.delete(birdie)
    db.session.commit()
    
    flash("Birdie deleted successfully", "success")
    return redirect(url_for('main.player_birdie_records', player_id=player_id))

@bp.route("/admin/edit_player/<int:player_id>", methods=["POST"])
def edit_player(player_id):
    if not session.get("is_admin"):
        flash("You do not have access to this page", "error")
        return redirect(url_for("login"))
    player = Player.query.get_or_404(player_id)
    player.name = request.form["name"].strip()
    db.session.commit()
    flash("Player name updated successfully!", "success")
    return redirect(url_for("main.admin_dashboard"))

@bp.route("/admin/edit_course/<int:course_id>", methods=["POST"])
def edit_course(course_id):
    if not session.get("is_admin"):
        flash("You do not have access to this page", "error")
        return redirect(url_for("login"))
    course = Course.query.get_or_404(course_id)
    course.name = request.form["name"].strip()
    db.session.commit()
    flash("Course name updated successfully!", "success")
    return redirect(url_for("main.admin_dashboard"))

@bp.route("/admin/edit_birdie/<int:birdie_id>", methods=["POST"])
def edit_birdie(birdie_id):
    if not session.get("is_admin"):
        flash("You do not have access to this page", "error")
        return redirect(url_for("login"))
    birdie = Birdie.query.get_or_404(birdie_id)
    birdie.date = datetime.strptime(request.form["date"], "%Y-%m-%d")
    db.session.commit()
    flash("Birdie date updated successfully!", "success")
    return redirect(url_for("main.admin_player_birdies", player_id=birdie.player_id))

@bp.route("/add_emoji", methods=["GET", "POST"])
def add_emoji():
    if request.method == "POST":
        player_id = request.form["player_id"]
        emoji = request.form["emoji"]
        player = Player.query.get_or_404(player_id)
        if player.permanent_emojis is None:
            player.permanent_emojis = ""
        player.permanent_emojis += emoji
        db.session.commit()
        flash("Emoji added successfully!", "success")
        return redirect(url_for("main.leaderboard"))
    players = Player.query.all()
    return render_template("add_emoji.html", players=players)

@bp.route("/history", methods=["GET"])
def history():
    current_year = datetime.now().year
    selected_year = request.args.get('year', current_year, type=int)
    
    if selected_year == current_year:
        players = db.session.query(
            Player,
            func.count(Birdie.id).label('birdie_count'),
            func.sum(case((Birdie.is_eagle == True, 1), else_=0)).label('eagle_count')
        ).outerjoin(
            Birdie, 
            (Player.id == Birdie.player_id) & (Birdie.year == selected_year)
        ).group_by(Player.id).having(
            func.count(Birdie.id) > 0
        ).all()
    else:
        players = db.session.query(
            Player,
            HistoricalTotal.birdies.label('birdie_count'),
            HistoricalTotal.eagles.label('eagle_count'),
            HistoricalTotal.has_trophy.label('has_trophy')
        ).join(
            HistoricalTotal,
            (Player.id == HistoricalTotal.player_id) & 
            (HistoricalTotal.year == selected_year)
        ).filter(
            or_(
                HistoricalTotal.birdies > 0,
                HistoricalTotal.eagles > 0
            )
        ).all()

    # Create initial leaderboard with totals
    leaderboard = []
    for player_data in players:
        if selected_year == current_year:
            player, birdie_count, eagle_count = player_data
            has_trophy = "🏆" in (player.permanent_emojis or "")
        else:
            player, birdie_count, eagle_count, has_trophy = player_data
        
        total = birdie_count + eagle_count
        
        leaderboard.append((
            total,  # Store total for sorting
            player.name,
            birdie_count,
            player.id,
            "🏆" if has_trophy else "",
            eagle_count
        ))
    
    # Sort by total score (descending)
    sorted_leaderboard = sorted(leaderboard, key=lambda x: x[0], reverse=True)
    
    # Create final leaderboard with ranks
    final_leaderboard = []
    prev_total = None
    current_rank = 0
    players_at_rank = 1
    
    for idx, entry in enumerate(sorted_leaderboard):
        total = entry[0]
        
        if total != prev_total:
            current_rank = idx + 1
            players_at_rank = 1
        else:
            players_at_rank += 1
            # If this is the second player at this rank, also update the previous player
            if players_at_rank == 2 and final_leaderboard:
                prev_entry = final_leaderboard[-1]
                final_leaderboard[-1] = (f"T{current_rank}", *prev_entry[1:])
        
        rank_display = f"T{current_rank}" if players_at_rank > 1 else str(current_rank)
        prev_total = total
        
        final_leaderboard.append((
            rank_display,
            entry[1],  # name
            entry[2],  # birdies
            entry[3],  # player_id
            entry[4],  # trophy
            entry[5]   # eagles
        ))

    # Get list of available years
    db_years = db.session.query(
        db.distinct(Birdie.year)
    ).filter(
        Birdie.year.isnot(None)
    ).union(
        db.session.query(
            db.distinct(HistoricalTotal.year)
        ).filter(
            HistoricalTotal.year.isnot(None),
            or_(
                HistoricalTotal.birdies > 0,
                HistoricalTotal.eagles > 0
            )
        )
    ).all()
    
    years = [year[0] for year in db_years]
    
    # Always include current year
    if current_year not in years:
        years.append(current_year)
    
    # Sort years in descending order
    years = sorted(list(set(years)), reverse=True)

    return render_template(
        "history.html",
        leaderboard=final_leaderboard,
        selected_year=selected_year,
        years=years
    )

@bp.route("/add_trophy", methods=["GET", "POST"])
def add_trophy():
    if not session.get("is_admin"):
        flash("You do not have access to this page", "error")
        return redirect(url_for("main.login"))

    if request.method == "POST":
        try:
            player_id = request.form.get("player_id")
            year = int(request.form.get("year", datetime.now().year))
            print(f"\nAdding trophy - Player ID: {player_id}, Year: {year}")
            
            player = Player.query.get(player_id)
            print(f"Found player: {player.name if player else None}")
            print(f"Player before update - permanent_emojis: {player.permanent_emojis}")
            
            if player:
                # Get or create historical total
                historical_total = HistoricalTotal.query.filter_by(
                    player_id=player_id,
                    year=year
                ).first()
                
                if not historical_total:
                    print("Creating new historical total")
                    historical_total = HistoricalTotal(
                        player_id=player_id,
                        year=year,
                        birdies=0,
                        eagles=0,
                        has_trophy=True
                    )
                    db.session.add(historical_total)
                else:
                    print("Updating existing historical total")
                    historical_total.has_trophy = True
                
                # Update player's trophy status regardless of current emojis
                if not player.permanent_emojis:
                    player.permanent_emojis = "🏆"
                elif "🏆" not in player.permanent_emojis:
                    player.permanent_emojis += "🏆"
                
                try:
                    db.session.commit()
                    print("Changes committed to database")
                    # Verify changes after commit
                    db.session.refresh(player)
                    db.session.refresh(historical_total)
                    print(f"Player after commit - permanent_emojis: {player.permanent_emojis}")
                    print(f"Historical total after commit - has_trophy: {historical_total.has_trophy}")
                except Exception as commit_error:
                    print(f"Error during commit: {commit_error}")
                    db.session.rollback()
                    raise
                
                flash(f"Trophy added to {player.name}!", "success")
            else:
                flash("Player not found!", "error")
            
            return redirect(url_for("main.admin_dashboard"))
        except Exception as e:
            print(f"Error adding trophy: {e}")
            flash("An error occurred while adding the trophy.", "error")
            db.session.rollback()
            return redirect(url_for("main.admin_dashboard"))
    
    players = Player.query.all()
    return render_template("add_trophy.html", players=players)

@bp.route("/add_historical_totals", methods=['GET', 'POST'])
@login_required
def add_historical_totals():
    current_year = datetime.now().year
    selected_year = 2024  # Default to 2024
    years = range(2020, current_year + 1)
    
    if request.method == "POST":
        try:
            print("\nForm Data:")
            for key, value in request.form.items():
                print(f"{key}: {value}")
            
            year = int(request.form.get("year"))
            print(f"\nProcessing year: {year}")
            
            # Get all player IDs and their totals from the form
            for key, value in request.form.items():
                if key.startswith('birdies_'):
                    try:
                        player_id = int(key.split('_')[1])
                        birdies = int(value) if value else 0
                        eagles = int(request.form.get(f'eagles_{player_id}', 0) or 0)  # Handle empty string
                        has_trophy = request.form.get(f'trophy_{player_id}', 'off') == 'on'
                        
                        print(f"\nProcessing player {player_id}:")
                        print(f"Birdies: {birdies}")
                        print(f"Eagles: {eagles}")
                        print(f"Trophy: {has_trophy}")
                        
                        # Update or create the historical total
                        historical_total = HistoricalTotal.query.filter_by(
                            player_id=player_id,
                            year=year
                        ).first()
                        
                        if historical_total:
                            print(f"Updating existing record")
                            historical_total.birdies = birdies
                            historical_total.eagles = eagles
                            historical_total.has_trophy = has_trophy
                            print(f"Updated values - Birdies: {historical_total.birdies}, Eagles: {historical_total.eagles}, Trophy: {historical_total.has_trophy}")
                        else:
                            print(f"Creating new record")
                            historical_total = HistoricalTotal(
                                player_id=player_id,
                                year=year,
                                birdies=birdies,
                                eagles=eagles,
                                has_trophy=has_trophy
                            )
                            db.session.add(historical_total)
                            print("New record added to session")
                        
                        # Update player's trophy status if needed
                        if has_trophy:
                            player = Player.query.get(player_id)
                            if player:
                                if not player.permanent_emojis:
                                    player.permanent_emojis = "🏆"
                                elif "🏆" not in player.permanent_emojis:
                                    player.permanent_emojis += "🏆"
                                print(f"Updated player trophy status: {player.permanent_emojis}")
                    except Exception as player_error:
                        print(f"Error processing player {player_id}: {str(player_error)}")
                        raise
            
            print("\nCommitting to database...")
            db.session.commit()
            print("Commit successful!")
            
            # Verify the data was saved correctly
            for key, value in request.form.items():
                if key.startswith('birdies_'):
                    player_id = int(key.split('_')[1])
                    historical = HistoricalTotal.query.filter_by(
                        player_id=player_id,
                        year=year
                    ).first()
                    if historical:
                        print(f"Verified player {player_id}: Birdies={historical.birdies}, Eagles={historical.eagles}, Trophy={historical.has_trophy}")
            
            flash(f"Historical totals updated for {year}", "success")
            return redirect(url_for("main.history", year=year))

        except Exception as e:
            print(f"\nError adding historical totals: {str(e)}")
            import traceback
            print(traceback.format_exc())
            flash("An error occurred while adding historical totals.", "error")
            return redirect(url_for("main.add_historical_totals"))

    # For GET request
    players = Player.query.all()
    return render_template('add_historical_totals.html', 
        players=players,
        current_year=current_year,
        selected_year=selected_year,
        years=years)

@bp.route("/debug_eagles/<int:player_id>")
def debug_eagles(player_id):
    current_year = datetime.now().year
    eagles = Birdie.query.filter_by(
        player_id=player_id,
        year=current_year,
        is_eagle=True
    ).all()
    
    result = []
    for eagle in eagles:
        result.append({
            'id': eagle.id,
            'date': eagle.date,
            'course': eagle.course.name,
            'is_eagle': eagle.is_eagle
        })
    
    return jsonify(result)

@bp.route("/debug_player/<int:player_id>")
def debug_player(player_id):
    player = Player.query.get_or_404(player_id)
    return jsonify({
        'name': player.name,
        'permanent_emojis': player.permanent_emojis,
        'id': player.id
    })

@bp.route("/reset_permanent_emojis/<int:player_id>")
def reset_permanent_emojis(player_id):
    player = Player.query.get_or_404(player_id)
    player.permanent_emojis = None  # or "" if you prefer
    db.session.commit()
    flash("Permanent emojis have been reset", "success")
    return redirect(url_for('main.leaderboard'))

@bp.route("/trends")
def trends():
    # Get all years from both current and historical data
    years = db.session.query(
        db.distinct(Birdie.year)
    ).filter(
        Birdie.year.isnot(None)
    ).union(
        db.session.query(
            db.distinct(HistoricalTotal.year)
        ).filter(
            HistoricalTotal.year.isnot(None)
        )
    ).all()
    
    years = sorted([year[0] for year in years], reverse=True)
    
    # Get all players
    players = Player.query.all()
    
    # Get yearly totals for each player
    player_stats = {}
    for player in players:
        yearly_stats = []
        for year in years:
            # Get current year stats
            if year == datetime.now().year:
                stats = db.session.query(
                    func.count(Birdie.id).label('birdies'),
                    func.sum(case((Birdie.is_eagle == True, 1), else_=0)).label('eagles')
                ).filter(
                    Birdie.player_id == player.id,
                    Birdie.year == year
                ).first()
                birdies = stats[0] or 0
                eagles = stats[1] or 0
            else:
                # Get historical stats
                historical = HistoricalTotal.query.filter_by(
                    player_id=player.id,
                    year=year
                ).first()
                birdies = historical.birdies if historical else 0
                eagles = historical.eagles if historical else 0
            
            yearly_stats.append({
                'year': year,
                'birdies': birdies,
                'eagles': eagles,
                'total': birdies + eagles
            })
        
        player_stats[player.name] = yearly_stats
    
    print("Debug - Years:", years)
    print("Debug - Players:", [p.name for p in players])
    print("Debug - Player Stats:", player_stats)
    
    return render_template(
        'trends.html',
        years=years,
        players=players,
        player_stats=player_stats
    )

@bp.route("/delete_trophy/<int:player_id>")
@login_required
def delete_trophy(player_id):
    player = Player.query.get_or_404(player_id)
    if player.has_trophy:
        player.has_trophy = False
        db.session.commit()
        flash(f'Trophy removed from {player.name}')
    else:
        flash(f'{player.name} does not have a trophy')
    return redirect(url_for('main.admin_dashboard'))

@bp.route("/delete_score/<int:score_id>", methods=['POST'])
@login_required
def delete_score(score_id):
    if not current_user.is_admin:
        flash('You do not have permission to delete scores.')
        return redirect(url_for('main.leaderboard'))
        
    try:
        score = Birdie.query.get_or_404(score_id)
        db.session.delete(score)
        db.session.commit()
        flash('Score deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting score: {str(e)}', 'error')
    
    return redirect(url_for('main.admin_dashboard'))

@bp.route("/tournaments")
def tournaments():
    # Check if site password is required
    auth_redirect = check_site_auth()
    if auth_redirect:
        return auth_redirect
        
    # Get the selected year (default to current year)
    selected_year = request.args.get('year', datetime.now().year, type=int)
    
    # Get all years that have tournaments
    years_with_tournaments = db.session.query(
        func.distinct(Tournament.year)
    ).order_by(Tournament.year.desc()).all()
    
    years = [year[0] for year in years_with_tournaments]
    
    # If no tournaments exist yet, use current year
    if not years:
        years = [datetime.now().year]
    
    # If selected year is not in the list, use the first year
    if selected_year not in years:
        selected_year = years[0]
    
    # Get tournaments for the selected year
    tournaments = Tournament.query.filter_by(year=selected_year).order_by(Tournament.date.desc()).all()
    
    return render_template(
        'tournaments.html',
        tournaments=tournaments,
        selected_year=selected_year,
        years=years
    )

@bp.route("/tournament/<int:tournament_id>")
def tournament_details(tournament_id):
    # Check if site password is required
    auth_redirect = check_site_auth()
    if auth_redirect:
        return auth_redirect
        
    # Get the tournament
    tournament = Tournament.query.get_or_404(tournament_id)
    
    # Get results for this tournament
    results = TournamentResult.query.filter_by(tournament_id=tournament.id).order_by(TournamentResult.position).all()
    
    return render_template(
        'tournament_details.html',
        tournament=tournament,
        results=results
    )

@bp.route("/admin/tournaments")
@login_required
def admin_tournaments():
    if not current_user.is_admin:
        flash('You do not have permission to access this page.')
        return redirect(url_for('main.leaderboard'))
    
    tournaments = Tournament.query.order_by(Tournament.date.desc()).all()
    courses = Course.query.all()
    
    return render_template(
        "admin_tournaments.html",
        tournaments=tournaments,
        courses=courses
    )

@bp.route("/admin/add_tournament", methods=['GET', 'POST'])
@login_required
def add_tournament():
    if not current_user.is_admin:
        flash('You do not have permission to access this page.')
        return redirect(url_for('main.leaderboard'))
    
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            date_str = request.form.get('date')
            course_id = request.form.get('course_id')
            is_team_event = request.form.get('is_team_event') == 'on'
            description = request.form.get('description')
            
            # Parse date
            date = datetime.strptime(date_str, '%Y-%m-%d')
            year = date.year
            
            # Create tournament
            tournament = Tournament(
                name=name,
                date=date,
                course_id=course_id,
                is_team_event=is_team_event,
                description=description,
                year=year
            )
            
            db.session.add(tournament)
            db.session.commit()
            
            flash(f'Tournament "{name}" added successfully!', 'success')
            return redirect(url_for('main.admin_tournaments'))
            
        except Exception as e:
            db.session.rollback()
            print(f"Error adding tournament: {e}")
            flash('Error adding tournament. Please try again.', 'error')
    
    courses = Course.query.all()
    return render_template(
        "add_tournament.html",
        courses=courses
    )

@bp.route("/admin/edit_tournament/<int:tournament_id>", methods=['GET', 'POST'])
@login_required
def edit_tournament(tournament_id):
    if not current_user.is_admin:
        flash('You do not have permission to access this page.')
        return redirect(url_for('main.leaderboard'))
    
    tournament = Tournament.query.get_or_404(tournament_id)
    
    if request.method == 'POST':
        try:
            tournament.name = request.form.get('name')
            tournament.date = datetime.strptime(request.form.get('date'), '%Y-%m-%d')
            tournament.course_id = request.form.get('course_id')
            tournament.is_team_event = request.form.get('is_team_event') == 'on'
            tournament.description = request.form.get('description')
            tournament.year = tournament.date.year
            
            db.session.commit()
            
            flash(f'Tournament "{tournament.name}" updated successfully!', 'success')
            return redirect(url_for('main.admin_tournaments'))
            
        except Exception as e:
            db.session.rollback()
            print(f"Error updating tournament: {e}")
            flash('Error updating tournament. Please try again.', 'error')
    
    courses = Course.query.all()
    return render_template(
        "edit_tournament.html",
        tournament=tournament,
        courses=courses
    )

@bp.route("/admin/delete_tournament/<int:tournament_id>")
@login_required
def delete_tournament(tournament_id):
    if not current_user.is_admin:
        flash('You do not have permission to access this page.')
        return redirect(url_for('main.leaderboard'))
    
    tournament = Tournament.query.get_or_404(tournament_id)
    
    try:
        db.session.delete(tournament)
        db.session.commit()
        flash(f'Tournament "{tournament.name}" deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting tournament: {e}")
        flash('Error deleting tournament. Please try again.', 'error')
    
    return redirect(url_for('main.admin_tournaments'))

@bp.route("/admin/manage_teams")
@login_required
def manage_teams():
    if not current_user.is_admin:
        flash('You do not have permission to access this page.')
        return redirect(url_for('main.leaderboard'))
    
    teams = Team.query.all()
    players = Player.query.all()
    
    return render_template(
        "manage_teams.html",
        teams=teams,
        players=players
    )

@bp.route("/admin/add_team", methods=['POST'])
@login_required
def add_team():
    if not current_user.is_admin:
        flash('You do not have permission to access this page.')
        return redirect(url_for('main.leaderboard'))
    
    try:
        name = request.form.get('name')
        
        # Create team
        team = Team(name=name)
        db.session.add(team)
        db.session.commit()
        
        flash(f'Team "{name}" added successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        print(f"Error adding team: {e}")
        flash('Error adding team. Please try again.', 'error')
    
    return redirect(url_for('main.manage_teams'))

@bp.route("/admin/add_team_member", methods=['POST'])
@login_required
def add_team_member():
    if not current_user.is_admin:
        flash('You do not have permission to access this page.')
        return redirect(url_for('main.leaderboard'))
    
    try:
        team_id = request.form.get('team_id')
        player_id = request.form.get('player_id')
        
        # Check if player is already in the team
        existing_member = TeamMember.query.filter_by(
            team_id=team_id,
            player_id=player_id
        ).first()
        
        if existing_member:
            flash('Player is already a member of this team.', 'error')
            return redirect(url_for('main.manage_teams'))
        
        # Add player to team
        team_member = TeamMember(
            team_id=team_id,
            player_id=player_id
        )
        
        db.session.add(team_member)
        db.session.commit()
        
        team = Team.query.get(team_id)
        player = Player.query.get(player_id)
        
        flash(f'Added {player.name} to team "{team.name}" successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        print(f"Error adding team member: {e}")
        flash('Error adding team member. Please try again.', 'error')
    
    return redirect(url_for('main.manage_teams'))

@bp.route("/admin/remove_team_member/<int:team_member_id>")
@login_required
def remove_team_member(team_member_id):
    if not current_user.is_admin:
        flash('You do not have permission to access this page.')
        return redirect(url_for('main.leaderboard'))
    
    team_member = TeamMember.query.get_or_404(team_member_id)
    
    try:
        player_name = team_member.player.name
        team_name = team_member.team.name
        
        db.session.delete(team_member)
        db.session.commit()
        
        flash(f'Removed {player_name} from team "{team_name}" successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        print(f"Error removing team member: {e}")
        flash('Error removing team member. Please try again.', 'error')
    
    return redirect(url_for('main.manage_teams'))

@bp.route("/admin/add_tournament_result/<int:tournament_id>", methods=['GET', 'POST'])
@login_required
def add_tournament_result(tournament_id):
    if not current_user.is_admin:
        flash('You do not have permission to access this page.')
        return redirect(url_for('main.leaderboard'))
    
    tournament = Tournament.query.get_or_404(tournament_id)
    
    if request.method == 'POST':
        try:
            position = int(request.form.get('position'))
            score = request.form.get('score')
            
            if tournament.is_team_event:
                team_id = request.form.get('team_id')
                
                # Create result
                result = TournamentResult(
                    tournament_id=tournament_id,
                    team_id=team_id,
                    position=position,
                    score=score
                )
            else:
                player_id = request.form.get('player_id')
                
                # Create result
                result = TournamentResult(
                    tournament_id=tournament_id,
                    player_id=player_id,
                    position=position,
                    score=score
                )
            
            db.session.add(result)
            db.session.commit()
            
            flash('Tournament result added successfully!', 'success')
            return redirect(url_for('main.tournament_details', tournament_id=tournament_id))
            
        except Exception as e:
            db.session.rollback()
            print(f"Error adding tournament result: {e}")
            flash('Error adding tournament result. Please try again.', 'error')
    
    players = Player.query.all()
    teams = Team.query.all()
    
    return render_template(
        "add_tournament_result.html",
        tournament=tournament,
        players=players,
        teams=teams
    )