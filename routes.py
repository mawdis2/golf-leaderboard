# routes.py
from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash, get_flashed_messages, session
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy.sql import func, case, and_, or_, extract
from datetime import datetime, timedelta, timezone
from models import db, User, Player, Birdie, Course, HistoricalTotal, Eagle, Tournament, Team, TeamMember, TournamentResult, Match
from forms import TournamentForm, CourseForm

# Create a Blueprint
bp = Blueprint('main', __name__)

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
        
        # Check for trophy from tournament wins or historical data
        try:
            # Try to get trophy_count from historical_total
            historical_total = HistoricalTotal.query.filter(
                HistoricalTotal.player_id == player.id,
                HistoricalTotal.year == current_year,
                HistoricalTotal.has_trophy == True
            ).first()
            
            has_trophy = historical_total is not None
            trophy_count = getattr(historical_total, 'trophy_count', 0) if historical_total else 0
            
            # Double-check trophy count by counting tournament wins directly
            if has_trophy:
                # Count individual tournament wins
                individual_wins = TournamentResult.query.join(Tournament).filter(
                    TournamentResult.player_id == player.id,
                    TournamentResult.position == 1,
                    extract('year', Tournament.date) == current_year
                ).count()
                
                # Count team tournament wins
                team_wins = 0
                teams = Team.query.join(TeamMember).filter(TeamMember.player_id == player.id).all()
                for team in teams:
                    team_wins += TournamentResult.query.join(Tournament).filter(
                        TournamentResult.team_id == team.id,
                        TournamentResult.position == 1,
                        extract('year', Tournament.date) == current_year
                    ).count()
                
                # Use the direct count if it's different from the stored count
                actual_trophy_count = individual_wins + team_wins
                if actual_trophy_count != trophy_count and actual_trophy_count > 0:
                    trophy_count = actual_trophy_count
                    
                    # Update the historical total with the correct count
                    if historical_total:
                        historical_total.trophy_count = actual_trophy_count
                        db.session.commit()
            
        except Exception as e:
            # If trophy_count column doesn't exist yet, fall back to has_trophy
            historical_total = HistoricalTotal.query.filter(
                HistoricalTotal.player_id == player.id,
                HistoricalTotal.year == current_year,
                HistoricalTotal.has_trophy == True
            ).first()
            
            has_trophy = historical_total is not None
            trophy_count = 1 if has_trophy else 0
        
        total = birdie_count + eagle_count
        player.birdie_count = birdie_count
        player.eagle_count = eagle_count
        player.total = total
        player.has_trophy = has_trophy
        player.trophy_count = trophy_count
        
        # Initialize emojis string
        emojis = ""
        
        # Add trophies if player has won tournaments this year
        if has_trophy and trophy_count > 0:
            # Show up to 3 trophies on the leaderboard
            visible_trophies = min(trophy_count, 3)
            emojis += "🏆" * visible_trophies
            if trophy_count > 3:
                emojis += f"({trophy_count})"
        
        # Check for recent birdies (within last 7 days)
        seven_days_ago = datetime.now() - timedelta(days=7)
        recent_birdies = Birdie.query.filter(
            Birdie.player_id == player.id,
            Birdie.is_eagle == False,
            Birdie.date >= seven_days_ago,
            Birdie.year == current_year
        ).count()
        
        # Add one birdie emoji for each recent birdie
        if recent_birdies > 0:
            emojis += "🐤" * recent_birdies
            
        # Add eagle emojis for current year
        if eagle_count > 0:
            emojis += "🦅" * eagle_count
        
        player.emojis = emojis
            
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
    
    # Check if any player has a trophy
    show_trophy = any(player.has_trophy for player in player_scores)
    
    return render_template("leaderboard.html", players=player_scores, show_trophy=show_trophy, current_year=current_year)

@bp.route("/add_player", methods=["GET", "POST"])
def add_player():
    auth_check = check_site_auth()
    if auth_check:
        return auth_check
        
    if request.method == "POST":
        try:
            name = request.form["name"].strip()
            existing_player = Player.query.filter(func.lower(Player.name) == func.lower(name)).first()
            if existing_player:
                flash("Player with this name already exists.", "error")
                return redirect(url_for("add_player"))
                
            # Get the next available ID
            max_id = db.session.execute("SELECT MAX(id) FROM player").scalar()
            next_id = (max_id or 0) + 1
            
            # Create new player with explicit ID
            new_player = Player(
                id=next_id,  # Explicitly set the ID
                name=name,
                has_trophy=False,
                permanent_emojis=None
            )
            
            db.session.add(new_player)
            db.session.commit()
            
            # Reset the sequence to the next available ID
            db.session.execute(f"SELECT setval('player_id_seq', {next_id}, true)")
            db.session.commit()
            
            flash("Player added successfully!", "success")
            return redirect(url_for("main.leaderboard"))
            
        except Exception as e:
            flash(f"Error adding player: {str(e)}", "error")
            db.session.rollback()
            return redirect(url_for("add_player"))
            
    clear_flash_messages()
    return render_template("add_player.html")

@bp.route("/add_birdie", methods=['GET', 'POST'])
def add_birdie():
    if request.method == 'POST':
        try:
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
            
            is_eagle = True if is_eagle_raw == 'true' else False
            
            # Find the player
            player = Player.query.get(player_id)
            if player:
                # Create new birdie record
                new_record = Birdie(
                    player_id=player_id, 
                    course_id=course_id, 
                    hole_number=hole_number,
                    year=current_year,
                    date=date,
                    is_eagle=is_eagle
                )
                
                db.session.add(new_record)
                db.session.commit()
                flash('Score added successfully!', 'success')
            else:
                flash('Player not found.', 'error')
                
            return redirect(url_for('main.add_birdie'))
            
        except Exception as e:
            db.session.rollback()
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
        flash('Error loading page. Please try again.', 'error')
        return redirect(url_for('main.leaderboard'))

@bp.route("/add_course", methods=["GET", "POST"])
def add_course():
    if request.method == "POST":
        course_name = request.form.get("course_name")
        if course_name:
            try:
                # Check if course already exists
                existing_course = Course.query.filter(func.lower(Course.name) == func.lower(course_name)).first()
                if existing_course:
                    flash("A course with this name already exists.", "error")
                    return redirect(url_for("main.add_course"))
                
                # Get the next available ID
                max_id = db.session.execute("SELECT MAX(id) FROM course").scalar()
                next_id = (max_id or 0) + 1
                
                # Create new course with explicit ID
                course = Course(
                    id=next_id,  # Explicitly set the ID
                    name=course_name
                )
                db.session.add(course)
                db.session.commit()
                
                # Reset the sequence to the next available ID
                db.session.execute(f"SELECT setval('course_id_seq', {next_id}, true)")
                db.session.commit()
                
                flash(f'Course "{course_name}" added successfully!', 'success')
                return redirect(url_for("main.admin_dashboard"))
            except Exception as e:
                db.session.rollback()
                flash('Error adding course. Please try again.', 'error')
        else:
            flash('Course name is required.', 'error')
    
    return render_template("add_course.html")

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
    try:
        auth_check = check_site_auth()
        if auth_check:
            return auth_check
            
        current_year = datetime.now().year
        selected_year = request.args.get('year', current_year, type=int)
        
        # Get all years that have data
        years = set()
        
        # Get years from birdies
        birdie_years = db.session.query(Birdie.year).distinct().all()
        years.update(int(year[0]) for year in birdie_years if year[0] is not None)
        
        # Get years from historical totals
        historical_years = db.session.query(HistoricalTotal.year).distinct().all()
        years.update(int(year[0]) for year in historical_years if year[0] is not None)
        
        # Get years from tournaments
        tournament_years = db.session.query(extract('year', Tournament.date).label('year')).distinct().all()
        years.update(int(year[0]) for year in tournament_years if year[0] is not None)
        
        # Always include current year
        years.add(current_year)
        
        # Sort years in descending order
        years = sorted(list(years), reverse=True)
        
        # Get all players
        players = Player.query.all()
        leaderboard = []
        
        for player in players:
            # Count regular birdies (not eagles) from current year's birdie table
            birdie_count = Birdie.query.filter(
                Birdie.player_id == player.id,
                Birdie.year == selected_year,
                Birdie.is_eagle == False
            ).count()
            
            # Count eagles from current year's birdie table
            eagle_count = Birdie.query.filter(
                Birdie.player_id == player.id,
                Birdie.year == selected_year,
                Birdie.is_eagle == True
            ).count()
            
            # Get historical data
            historical_total = HistoricalTotal.query.filter(
                HistoricalTotal.player_id == player.id,
                HistoricalTotal.year == selected_year
            ).first()
            
            has_trophy = False
            trophy_count = 0
            if historical_total:
                has_trophy = historical_total.has_trophy
                trophy_count = getattr(historical_total, 'trophy_count', 0) or 0
                # Add historical birdies and eagles if this is not the current year
                if selected_year != current_year:
                    birdie_count = historical_total.birdies
                    eagle_count = historical_total.eagles
            
            # Create trophy display string
            trophy_display = ""
            if has_trophy and trophy_count > 0:
                trophy_display = "🏆" * min(trophy_count, 3)
                if trophy_count > 3:
                    trophy_display += f"({trophy_count})"
            
            # Only add to leaderboard if player has any scores or trophies
            if birdie_count > 0 or eagle_count > 0 or has_trophy:
                leaderboard.append((0, player.name, birdie_count, player.id, trophy_display, eagle_count, trophy_count))
        
        # Sort by total score (birdies + eagles)
        leaderboard.sort(key=lambda x: x[2] + x[5], reverse=True)
        
        # Assign ranks with ties
        current_rank = 1
        prev_total = None
        
        for i, entry in enumerate(leaderboard):
            if i == 0:
                # First player
                if len(leaderboard) > 1 and entry[2] + entry[5] == leaderboard[1][2] + leaderboard[1][5]:
                    entry = ("T" + str(current_rank),) + entry[1:]
                else:
                    entry = (str(current_rank),) + entry[1:]
            else:
                if entry[2] + entry[5] == prev_total:
                    entry = ("T" + str(current_rank),) + entry[1:]
                else:
                    current_rank = i + 1
                    if i < len(leaderboard) - 1 and entry[2] + entry[5] == leaderboard[i + 1][2] + leaderboard[i + 1][5]:
                        entry = ("T" + str(current_rank),) + entry[1:]
                    else:
                        entry = (str(current_rank),) + entry[1:]
            
            leaderboard[i] = entry
            prev_total = entry[2] + entry[5]
        
        return render_template(
            "history.html",
            leaderboard=leaderboard,
            years=years,
            selected_year=selected_year
        )
    except Exception as e:
        flash("An error occurred while loading the history page. Please try again.", "error")
        return redirect(url_for("main.leaderboard"))

@bp.route("/add_trophy", methods=["GET", "POST"])
def add_trophy():
    if request.method == "POST":
            player_id = request.form.get("player_id")
            year = int(request.form.get("year", datetime.now().year))
            
            player = Player.query.get(player_id)
            
            if player:
                # Get or create historical total
                historical_total = HistoricalTotal.query.filter_by(
                    player_id=player_id,
                    year=year
                ).first()
                
                if not historical_total:
                    historical_total = HistoricalTotal(
                        player_id=player_id,
                        year=year,
                        birdies=0,
                        eagles=0,
                        has_trophy=True
                    )
                    db.session.add(historical_total)
                else:
                    historical_total.has_trophy = True
                
                # Update player's trophy status regardless of current emojis
                if not player.permanent_emojis:
                    player.permanent_emojis = "🏆"
                elif "🏆" not in player.permanent_emojis:
                    player.permanent_emojis += "🏆"
                
                try:
                    db.session.commit()
                except Exception as commit_error:
                    db.session.rollback()
                    raise
                
                flash(f"Trophy added to {player.name}!", "success")
            else:
                flash("Player not found!", "error")
            
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
            for key, value in request.form.items():
                if key.startswith('birdies_'):
                    try:
                        player_id = int(key.split('_')[1])
                        birdies = int(value) if value else 0
                        eagles = int(request.form.get(f'eagles_{player_id}', 0) or 0)
                        has_trophy = request.form.get(f'trophy_{player_id}', 'off') == 'on'
                        
                        # Update or create the historical total
                        historical_total = HistoricalTotal.query.filter_by(
                            player_id=player_id,
                            year=selected_year
                        ).first()
                        
                        if historical_total:
                            historical_total.birdies = birdies
                            historical_total.eagles = eagles
                            historical_total.has_trophy = has_trophy
                        else:
                            historical_total = HistoricalTotal(
                                player_id=player_id,
                                year=selected_year,
                                birdies=birdies,
                                eagles=eagles,
                                has_trophy=has_trophy
                            )
                        
                        db.session.add(historical_total)
                        
                        # Update player's trophy status if needed
                        if has_trophy:
                            player = Player.query.get(player_id)
                            if player:
                                if not player.permanent_emojis:
                                    player.permanent_emojis = "🏆"
                                elif "🏆" not in player.permanent_emojis:
                                    player.permanent_emojis += "🏆"
                    except Exception as player_error:
                        raise
            
            db.session.commit()
            
            flash(f"Historical totals updated for {selected_year}", "success")
            return redirect(url_for("main.history", year=selected_year))

        except Exception as e:
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

    # Get course performance data
    course_stats = {}
    for player in players:
        course_data = {}
        # Get current year stats by course
        current_year = datetime.now().year
        course_query = db.session.query(
            Course.name,
            func.count(Birdie.id).label('total')
        ).join(
            Birdie, Birdie.course_id == Course.id
        ).filter(
            Birdie.player_id == player.id,
            Birdie.year == current_year
        ).group_by(
            Course.name
        ).all()
        
        for course_name, total in course_query:
            course_data[course_name] = total
        
        course_stats[player.name] = course_data

    # Get monthly trends for current year
    monthly_stats = {}
    for player in players:
        current_year = datetime.now().year
        monthly_data = [0] * 12  # Initialize with zeros for all months
        
        # Get current year monthly stats
        monthly_query = db.session.query(
            extract('month', Birdie.date).label('month'),
            func.count(Birdie.id).label('total')
        ).filter(
            Birdie.player_id == player.id,
            Birdie.year == current_year
        ).group_by(
            'month'
        ).all()
        
        for month, total in monthly_query:
            monthly_data[int(month) - 1] = total
        
        monthly_stats[player.name] = monthly_data
    
    return render_template(
        'trends.html',
        years=years,
        players=players,
        player_stats=player_stats,
        course_stats=course_stats,
        monthly_stats=monthly_stats
    )

@bp.route("/delete_trophy/<int:player_id>")
@login_required
def delete_trophy(player_id):
    player = Player.query.get_or_404(player_id)
    if player.has_trophy:
        player.has_trophy = False
        # Remove trophy emoji from permanent_emojis
        if player.permanent_emojis and "🏆" in player.permanent_emojis:
            player.permanent_emojis = player.permanent_emojis.replace("🏆", "")
            if not player.permanent_emojis.strip():  # If no emojis left
                player.permanent_emojis = None
        db.session.commit()
        flash(f'Trophy removed from {player.name}')
    else:
        flash(f'{player.name} does not have a trophy')
    return redirect(url_for('main.admin_dashboard'))

@bp.route("/delete_score/<int:score_id>", methods=['POST'])
@login_required
def delete_score(score_id):
    if not current_user.is_admin:
        flash('You do not have permission to delete scores.', 'error')
        return redirect(url_for('main.leaderboard'))
    
    try:
        # Verify CSRF token
        if not request.form.get('csrf_token'):
            flash('Invalid request. Please try again.', 'error')
            return redirect(url_for('main.admin_dashboard'))
            
        score = Birdie.query.get_or_404(score_id)
        db.session.delete(score)
        db.session.commit()
        flash('Score deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting score. Please try again.', 'error')
    
    return redirect(url_for('main.admin_dashboard'))

@bp.route("/debug_tournaments")
def debug_tournaments():
    # Get all tournaments
    tournaments = Tournament.query.all()
    
    result = []
    for t in tournaments:
        result.append({
            'id': t.id,
            'name': t.name,
            'date': str(t.date),
            'year': t.year,
            'date_year': t.date.year if t.date else None
        })
    
    # Also try direct SQL
    sql_years_query = """
    SELECT id, name, date, year, EXTRACT(YEAR FROM date) as date_year
    FROM tournament
    ORDER BY date DESC
    """
    sql_result = db.session.execute(sql_years_query)
    sql_tournaments = []
    for row in sql_result:
        sql_tournaments.append({
            'id': row[0],
            'name': row[1],
            'date': str(row[2]),
            'year': row[3],
            'date_year': int(row[4]) if row[4] else None
        })
    
    return jsonify({
        'orm_tournaments': result,
        'sql_tournaments': sql_tournaments
    })

@bp.route("/tournaments")
def tournaments():
    # Get the selected year (default to current year)
    selected_year = request.args.get('year', datetime.now().year, type=int)
    
    # Get all years that have tournaments
    tournament_years_query = """
    SELECT DISTINCT EXTRACT(YEAR FROM date) as year
    FROM tournament
    ORDER BY year DESC
    """
    tournament_years_result = db.session.execute(tournament_years_query)
    tournament_years = [int(row[0]) for row in tournament_years_result]
    
    # Get all years that have trophies
    trophy_years_query = """
    SELECT DISTINCT year
    FROM historical_total
    WHERE trophy_count > 0
    ORDER BY year DESC
    """
    trophy_years_result = db.session.execute(trophy_years_query)
    trophy_years = [int(row[0]) for row in trophy_years_result]
    
    # Combine and deduplicate years
    all_years = sorted(set(tournament_years + trophy_years), reverse=True)
    
    # If no years found, use current year
    if not all_years:
        all_years = [datetime.now().year]
    
    # If selected year is not in the list, use the first year
    if selected_year not in all_years and all_years:
        selected_year = all_years[0]
    
    # Get tournaments for the selected year
    tournaments = Tournament.query.filter(
        extract('year', Tournament.date) == selected_year
    ).order_by(Tournament.date.desc()).all()
    
    return render_template(
        'tournaments.html',
        tournaments=tournaments,
        selected_year=selected_year,
        years=all_years
    )

@bp.route("/tournament/<int:tournament_id>")
def tournament_details(tournament_id):
    tournament = Tournament.query.get_or_404(tournament_id)
    results = TournamentResult.query.filter_by(tournament_id=tournament_id).order_by(TournamentResult.position).all()
    return render_template('tournament_details.html', tournament=tournament, results=results)

@bp.route("/tournament/<int:tournament_id>/matches")
def tournament_matches(tournament_id):
    tournament = Tournament.query.get_or_404(tournament_id)
    matches = Match.query.filter_by(tournament_id=tournament_id).order_by(Match.date.desc()).all()
    courses = Course.query.all()
    players = Player.query.all()  # Get all players
    
    # Get all players who have played matches in this tournament
    players_in_tournament = set()
    for match in matches:
        players_in_tournament.add(match.player1_id)
        players_in_tournament.add(match.player2_id)
    
    # Get standings for players who have played matches
    standings = []
    for player_id in players_in_tournament:
        player = Player.query.get(player_id)
        # Calculate points: 1 for wins, 0.5 for ties
        points = sum(1 for match in matches if match.winner_id == player_id) + \
                sum(0.5 for match in matches if match.is_tie and (match.player1_id == player_id or match.player2_id == player_id))
        standings.append((player, points, 0))  # Rank will be calculated later
    
    # Sort standings by points (descending)
    standings.sort(key=lambda x: x[1], reverse=True)
    
    # Calculate ranks with proper tie handling
    current_rank = 1
    current_points = standings[0][1] if standings else 0
    
    for i, (player, points, _) in enumerate(standings):
        if points < current_points:
            current_rank = i + 1
            current_points = points
        
        # Check if this score is unique
        is_unique = True
        for j, (other_player, other_points, _) in enumerate(standings):
            if i != j and other_points == points:
                is_unique = False
                break
        
        # Set rank based on whether the score is unique
        rank = str(current_rank) if is_unique else f"T{current_rank}"
        standings[i] = (player, points, rank)
    
    return render_template('tournament_matches.html', 
                         tournament=tournament, 
                         matches=matches, 
                         courses=courses,
                         players=players,
                         standings=standings)

@bp.route("/tournament/<int:tournament_id>/add_match", methods=['POST'])
def add_match(tournament_id):
    tournament = Tournament.query.get_or_404(tournament_id)
    
    player1_id = request.form.get('player1_id')
    player2_id = request.form.get('player2_id')
    course_id = request.form.get('course_id')
    date_str = request.form.get('date')
    result = request.form.get('result')
    
    if not all([player1_id, player2_id, course_id, date_str]):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'Player 1, Player 2, Course, and Date are required.'}), 400
        flash('Player 1, Player 2, Course, and Date are required.', 'error')
        return redirect(url_for('main.tournament_matches', tournament_id=tournament_id))
    
    try:
        match_date = datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'Invalid date format.'}), 400
        flash('Invalid date format.', 'error')
        return redirect(url_for('main.tournament_matches', tournament_id=tournament_id))
    
    match = Match(
        tournament_id=tournament_id,
        player1_id=player1_id,
        player2_id=player2_id,
        course_id=course_id,
        date=match_date
    )
    
    if result:  # Only set result if one was provided
        if result == 'tie':
            match.is_tie = True
        elif result == 'player1':
            match.winner_id = player1_id
        elif result == 'player2':
            match.winner_id = player2_id
    
    db.session.add(match)
    db.session.commit()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'message': 'Match added successfully!'})
    flash('Match added successfully!', 'success')
    return redirect(url_for('main.tournament_matches', tournament_id=tournament_id))

@bp.route("/edit_match/<int:match_id>", methods=['POST'])
def edit_match(match_id):
    match = Match.query.get_or_404(match_id)
    
    player1_id = request.form.get('player1_id')
    player2_id = request.form.get('player2_id')
    course_id = request.form.get('course_id')
    date_str = request.form.get('date')
    result = request.form.get('result')
    
    if not all([player1_id, player2_id, course_id, date_str]):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'Player 1, Player 2, Course, and Date are required.'}), 400
        flash('Player 1, Player 2, Course, and Date are required.', 'error')
        return redirect(url_for('main.tournament_matches', tournament_id=match.tournament_id))
    
    try:
        match_date = datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'Invalid date format.'}), 400
        flash('Invalid date format.', 'error')
        return redirect(url_for('main.tournament_matches', tournament_id=match.tournament_id))
    
    match.player1_id = player1_id
    match.player2_id = player2_id
    match.course_id = course_id
    match.date = match_date
    match.winner_id = None
    match.is_tie = False
    
    if result == 'tie':
        match.is_tie = True
    elif result == 'player1':
        match.winner_id = player1_id
    elif result == 'player2':
        match.winner_id = player2_id
    
    db.session.commit()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'message': 'Match updated successfully!'})
    flash('Match updated successfully!', 'success')
    return redirect(url_for('main.tournament_matches', tournament_id=match.tournament_id))

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

@bp.route("/add_tournament", methods=['GET', 'POST'])
@login_required
def add_tournament():
    form = TournamentForm()
    form.course.choices = [(c.id, c.name) for c in Course.query.order_by(Course.name).all()]
    
    if form.validate_on_submit():
        tournament = Tournament(
            name=form.name.data,
            date=form.date.data,
            course_id=form.course.data,
            has_individual_matches=form.has_individual_matches.data,
            year=form.date.data.year  # Add the year field
        )
        db.session.add(tournament)
        db.session.commit()
        flash('Tournament added successfully!', 'success')
        return redirect(url_for('main.tournaments'))
    
    return render_template('add_tournament.html', form=form)

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
            
            end_date_str = request.form.get('end_date')
            tournament.end_date = datetime.strptime(end_date_str, '%Y-%m-%d') if end_date_str else None
            
            tournament.course_id = request.form.get('course_id') or None  # Make course optional
            tournament.is_team_event = request.form.get('is_team_event') == 'on'
            tournament.description = request.form.get('description')
            tournament.year = tournament.date.year
            
            db.session.commit()
            
            flash(f'Tournament "{tournament.name}" updated successfully!', 'success')
            return redirect(url_for('main.admin_tournaments'))
        
        except Exception as e:
            db.session.rollback()
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
                
                db.session.add(result)
                
                # Award trophies to team members if they won (position 1)
                if position == 1:
                    team = Team.query.get(team_id)
                    for member in team.team_members:
                        player = member.player
                        # Add trophy to player's permanent emojis if they don't have one yet
                        if not player.permanent_emojis:
                            player.permanent_emojis = "🏆"
                        elif "🏆" not in player.permanent_emojis:
                            player.permanent_emojis += "🏆"
                        
                        # Update or create historical total for current year
                        current_year = tournament.date.year
                        historical_total = HistoricalTotal.query.filter_by(
                            player_id=player.id,
                            year=current_year
                        ).first()
                        
                        if not historical_total:
                            # Count current year birdies and eagles
                            birdie_count = Birdie.query.filter(
                                Birdie.player_id == player.id,
                                Birdie.year == current_year,
                                Birdie.is_eagle == False
                            ).count()
                            
                            eagle_count = Birdie.query.filter(
                                Birdie.player_id == player.id,
                                Birdie.year == current_year,
                                Birdie.is_eagle == True
                            ).count()
                            
                            # Try to create with trophy_count
                            try:
                                historical_total = HistoricalTotal(
                                    player_id=player.id,
                                    year=current_year,
                                    birdies=birdie_count,
                                    eagles=eagle_count,
                                    has_trophy=True,
                                    trophy_count=1  # First trophy
                                )
                                db.session.add(historical_total)
                            except Exception as e:
                                print(f"Error creating historical total with trophy_count: {e}")
                                # Fall back to just has_trophy
                                historical_total = HistoricalTotal(
                                    player_id=player.id,
                                    year=current_year,
                                    birdies=birdie_count,
                                    eagles=eagle_count,
                                    has_trophy=True
                                )
                                db.session.add(historical_total)
                        else:
                            historical_total.has_trophy = True
                            # Try to increment trophy_count
                            try:
                                if hasattr(historical_total, 'trophy_count'):
                                    historical_total.trophy_count += 1
                                else:
                                    historical_total.trophy_count = 1
                            except Exception as e:
                                print(f"Error updating trophy_count: {e}")
                                # If trophy_count doesn't exist, just set has_trophy
                                historical_total.has_trophy = True
                    
                    flash(f'Trophy awarded to all members of team {team.name}!', 'success')
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
                
                # Award trophy to player if they won (position 1)
                if position == 1:
                    player = Player.query.get(player_id)
                    # Add trophy to player's permanent emojis if they don't have one yet
                    if not player.permanent_emojis:
                        player.permanent_emojis = "🏆"
                    elif "🏆" not in player.permanent_emojis:
                        player.permanent_emojis += "🏆"
                    
                    # Update or create historical total for current year
                    current_year = tournament.date.year
                    historical_total = HistoricalTotal.query.filter_by(
                        player_id=player_id,
                        year=current_year
                    ).first()
                    
                    if not historical_total:
                        # Count current year birdies and eagles
                        birdie_count = Birdie.query.filter(
                            Birdie.player_id == player_id,
                            Birdie.year == current_year,
                            Birdie.is_eagle == False
                        ).count()
                        
                        eagle_count = Birdie.query.filter(
                            Birdie.player_id == player_id,
                            Birdie.year == current_year,
                            Birdie.is_eagle == True
                        ).count()
                        
                        # Try to create with trophy_count
                        try:
                            historical_total = HistoricalTotal(
                                player_id=player_id,
                                year=current_year,
                                birdies=birdie_count,
                                eagles=eagle_count,
                                has_trophy=True,
                                trophy_count=1  # First trophy
                            )
                            db.session.add(historical_total)
                        except Exception as e:
                            print(f"Error creating historical total with trophy_count: {e}")
                            # Fall back to just has_trophy
                            historical_total = HistoricalTotal(
                                player_id=player_id,
                                year=current_year,
                                birdies=birdie_count,
                                eagles=eagle_count,
                                has_trophy=True
                            )
                            db.session.add(historical_total)
                    else:
                        historical_total.has_trophy = True
                        # Try to increment trophy_count
                        try:
                            if hasattr(historical_total, 'trophy_count'):
                                historical_total.trophy_count += 1
                            else:
                                historical_total.trophy_count = 1
                        except Exception as e:
                            print(f"Error updating trophy_count: {e}")
                            # If trophy_count doesn't exist, just set has_trophy
                            historical_total.has_trophy = True
                    
                    flash(f'Trophy awarded to {player.name}!', 'success')
            
            db.session.commit()
            
            flash('Tournament result added successfully!', 'success')
            return redirect(url_for('main.tournament_details', tournament_id=tournament_id))
            
        except Exception as e:
            db.session.rollback()
            flash('Error adding tournament result. Please try again.', 'error')
    
    players = Player.query.all()
    teams = Team.query.all()
    
    return render_template(
        "add_tournament_result.html",
        tournament=tournament,
        players=players,
        teams=teams
    )

@bp.route("/debug_all_data")
def debug_all_data():
    # Debug tournaments
    tournaments = Tournament.query.all()
    tournament_data = []
    for t in tournaments:
        tournament_data.append({
            'id': t.id,
            'name': t.name,
            'date': str(t.date),
            'year': t.year,
            'date_year': t.date.year if t.date else None
        })
    
    # Debug historical totals with trophies
    trophy_data = []
    trophy_years_query = """
    SELECT player_id, year, has_trophy, trophy_count 
    FROM historical_total 
    WHERE has_trophy = true OR trophy_count > 0
    ORDER BY year DESC, player_id
    """
    trophy_results = db.session.execute(trophy_years_query)
    for row in trophy_results:
        player = Player.query.get(row[0])
        trophy_data.append({
            'player_id': row[0],
            'player_name': player.name if player else 'Unknown',
            'year': row[1],
            'has_trophy': row[2],
            'trophy_count': row[3] if len(row) > 3 else None
        })
    
    # Debug tournament results
    results_data = []
    results = TournamentResult.query.filter_by(position=1).all()  # Winners only
    for result in results:
        tournament = Tournament.query.get(result.tournament_id) if result.tournament_id else None
        player = Player.query.get(result.player_id) if result.player_id else None
        team = Team.query.get(result.team_id) if result.team_id else None
        
        results_data.append({
            'id': result.id,
            'tournament_id': result.tournament_id,
            'tournament_name': tournament.name if tournament else None,
            'tournament_date': str(tournament.date) if tournament and tournament.date else None,
            'tournament_year': tournament.year if tournament else None,
            'player_id': result.player_id,
            'player_name': player.name if player else None,
            'team_id': result.team_id,
            'team_name': team.name if team else None,
            'position': result.position,
            'score': result.score
        })
    
    # Debug direct SQL queries for years
    tournament_years_query = """
    SELECT DISTINCT EXTRACT(YEAR FROM date) as year
    FROM tournament
    ORDER BY year DESC
    """
    tournament_years_result = db.session.execute(tournament_years_query)
    tournament_years = [int(row[0]) for row in tournament_years_result]
    
    trophy_years_query = """
    SELECT DISTINCT year
    FROM historical_total
    WHERE trophy_count > 0 OR has_trophy = true
    ORDER BY year DESC
    """
    trophy_years_result = db.session.execute(trophy_years_query)
    trophy_years = [int(row[0]) for row in trophy_years_result]
    
    # Combine and deduplicate years
    all_years = sorted(set(tournament_years + trophy_years), reverse=True)
    
    return jsonify({
        'tournaments': tournament_data,
        'trophy_records': trophy_data,
        'tournament_results': results_data,
        'tournament_years': tournament_years,
        'trophy_years': trophy_years,
        'combined_years': all_years
    })

@bp.route('/admin/fix_trophies', methods=['GET'])
@login_required
def admin_fix_trophies():
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('main.leaderboard'))
    
    flash('Trophy records are automatically synchronized with tournament results.', 'info')
    return redirect(url_for('main.admin_dashboard'))

@bp.route("/hot_streaks")
def hot_streaks():
    players = Player.query.order_by(Player.name).all()
    return render_template('hot_streaks.html', players=players)

@bp.route("/tournament/<int:tournament_id>/finish", methods=['POST'])
def finish_tournament(tournament_id):
    tournament = Tournament.query.get_or_404(tournament_id)
    
    if not tournament.is_active:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'Tournament is already finished.'}), 400
        flash('Tournament is already finished.', 'error')
        return redirect(url_for('main.tournament_matches', tournament_id=tournament_id))
    
    # Get the standings
    standings = tournament.get_standings()
    if not standings:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'No matches have been played yet.'}), 400
        flash('No matches have been played yet.', 'error')
        return redirect(url_for('main.tournament_matches', tournament_id=tournament_id))
    
    # Get the winner (first player in standings)
    winner = standings[0][0]
    
    # Update the winner's trophy status
    winner.has_trophy = True
    
    # Update or create historical total for the winner
    current_year = datetime.now().year
    historical_total = HistoricalTotal.query.filter(
        HistoricalTotal.player_id == winner.id,
        HistoricalTotal.year == current_year
    ).first()
    
    if historical_total:
        historical_total.has_trophy = True
        historical_total.trophy_count += 1
    else:
        historical_total = HistoricalTotal(
            player_id=winner.id,
            year=current_year,
            has_trophy=True,
            trophy_count=1
        )
        db.session.add(historical_total)
    
    # Mark tournament as finished
    tournament.is_active = False
    
    db.session.commit()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'message': f'Tournament finished! {winner.name} wins!'})
    flash(f'Tournament finished! {winner.name} wins!', 'success')
    return redirect(url_for('main.tournament_matches', tournament_id=tournament_id))

@bp.route("/delete_match/<int:match_id>", methods=['POST'])
def delete_match(match_id):
    match = Match.query.get_or_404(match_id)
    
    # Delete the match
    db.session.delete(match)
    db.session.commit()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'message': 'Match deleted successfully'})
    
    flash('Match deleted successfully', 'success')
    return redirect(url_for('main.tournament_matches', tournament_id=match.tournament_id))