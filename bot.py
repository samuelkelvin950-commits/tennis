# bot.py
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from dotenv import load_dotenv
import os

# Load Telegram token from environment variable
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

# Store last prediction
last_prediction = {}

# Welcome and Help messages
WELCOME_MESSAGE = """
🎾 Welcome to Tennis Predictor Bot!

I can analyze tennis match data and predict:
- Total games per set
- Set win probabilities
- Over/Under likelihood

Use /Help to see commands.
"""

HELP_MESSAGE = """
Commands:
/Start - Show welcome message
/Predict - Input match data and get predictions
/Result - Show last prediction
/Help - Show this help message
"""

# Validate input data
def validate_input(data: dict):
    try:
        required_keys = ['player_a','player_b','player_a_sets','player_b_sets','over_under','surface']
        for key in required_keys:
            if key not in data:
                return False, f"Missing field: {key}"

        if not all(isinstance(x,(int,float)) for x in data['player_a_sets']):
            return False, "player_a_sets must be numbers"
        if not all(isinstance(x,(int,float)) for x in data['player_b_sets']):
            return False, "player_b_sets must be numbers"
        if not isinstance(data['over_under'], (int,float)):
            return False, "over_under must be a number"

        return True, "Valid data"
    except Exception as e:
        return False, str(e)

# Prediction logic
def predict(data: dict):
    total_per_set = [a+b for a,b in zip(data['player_a_sets'], data['player_b_sets'])]
    avg_total = sum(total_per_set)/len(total_per_set)

    # Optional adjustment (0.2-0.5)
    adjustment = 0.3
    adjusted_total = avg_total + adjustment

    # Set Win Percentages
    player_a_win_pct = [a/(a+b)*100 if (a+b)>0 else 50 for a,b in zip(data['player_a_sets'], data['player_b_sets'])]
    player_b_win_pct = [100 - pct for pct in player_a_win_pct]

    # Normalize
    total_pct_a = sum(player_a_win_pct)
    total_pct_b = sum(player_b_win_pct)
    player_a_norm = total_pct_a / (total_pct_a + total_pct_b) * 100
    player_b_norm = 100 - player_a_norm

    # Over/Under prediction
    over_under_prediction = "Over" if adjusted_total > data['over_under'] else "Under"

    # Optional surface boost
    if data['surface'].lower() == 'clay':
        player_a_norm += 1
        player_b_norm -= 1

    result = {
        "total_per_set": total_per_set,
        "adjusted_total_games": round(adjusted_total,2),
        "player_a_win_pct": round(player_a_norm,2),
        "player_b_win_pct": round(player_b_norm,2),
        "over_under_prediction": over_under_prediction
    }
    return result

# Command handlers
def start(update: Update, context: CallbackContext):
    update.message.reply_text(WELCOME_MESSAGE)

def help_command(update: Update, context: CallbackContext):
    update.message.reply_text(HELP_MESSAGE)

def result_command(update: Update, context: CallbackContext):
    if last_prediction:
        msg = f"Last Prediction:\n{last_prediction}"
    else:
        msg = "No predictions yet. Use /Predict first."
    update.message.reply_text(msg)

def predict_command(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Send match data as CSV format:\n"
        "player_a,player_b,player_a_sets (space-separated),player_b_sets (space-separated),over_under,surface\n"
        "Example:\n"
        "Nadal,Federer,6 6,4 7,22.5,hard"
    )

def handle_message(update: Update, context: CallbackContext):
    global last_prediction
    text = update.message.text
    try:
        parts = text.split(',')
        data = {
            "player_a": parts[0].strip(),
            "player_b": parts[1].strip(),
            "player_a_sets": [int(x) for x in parts[2].strip().split()],
            "player_b_sets": [int(x) for x in parts[3].strip().split()],
            "over_under": float(parts[4].strip()),
            "surface": parts[5].strip()
        }

        valid, msg = validate_input(data)
        if not valid:
            update.message.reply_text(f"Invalid data: {msg}")
            return

        last_prediction = predict(data)
        update.message.reply_text(f"Prediction Result:\n{last_prediction}")

    except Exception as e:
        update.message.reply_text(f"Error processing data: {e}\nFollow the format exactly.")

# Main
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("Start", start))
    dp.add_handler(CommandHandler("Help", help_command))
    dp.add_handler(CommandHandler("Result", result_command))
    dp.add_handler(CommandHandler("Predict", predict_command))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
