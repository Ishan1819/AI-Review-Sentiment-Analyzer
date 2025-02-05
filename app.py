from flask import Flask, request, jsonify, render_template
from supabase import create_client, Client
from textblob import TextBlob
import nltk
nltk.download('punkt')
nltk.download('averaged_perceptron_tagger')
nltk.download('wordnet')

# Supabase initialization
supabase_url = "https://rnejwdzvyoaunmmewvar.supabase.co"
supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJuZWp3ZHp2eW9hdW5tbWV3dmFyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Mzg2MDYzOTMsImV4cCI6MjA1NDE4MjM5M30.MG1nN-r4Jfw80pGDND3gKICAxevvleTU4LaJ20H9ay0"
supabase: Client = create_client(supabase_url, supabase_key)

app = Flask(__name__)

# Function to get sentiment from the review text using TextBlob
def get_sentiment(review_text: str) -> str:
    try:
        blob = TextBlob(review_text)
        sentiment_score = blob.sentiment.polarity
        
        if sentiment_score > 0:
            return 'positive'
        else:
            return 'negative'
    except Exception as e:
        print(f"Error getting sentiment: {e}")
        raise Exception("Error getting sentiment")

# Function to add review to Supabase
def add_review_to_db(sentiment: str, review_text: str):
    """Insert sentiment review into Supabase"""
    data = {
        "positive": review_text if sentiment == "positive" else None,
        "negative": review_text if sentiment == "negative" else None,
    }

    # Handle None as NULL for Supabase
    if data["positive"] is None:
        data["positive"] = None
    if data["negative"] is None:
        data["negative"] = None

    response = supabase.table("review").insert(data).execute()
    print(response)  # Debugging step to inspect the response

    if response.data is None:
        raise Exception("Error adding review to database")


# Route to render the HTML form
@app.route('/')
def home():
    return render_template('index.html')  # Render the HTML form

def get_reviews_from_db(limit=100):
    """Fetch the last `limit` reviews from the Supabase database."""
    response = supabase.table("review").select("positive", "negative").order("id", desc=True).limit(limit).execute()
    if response.data:
        return response.data
    else:
        return []

def summarize_reviews(reviews):
    """Summarize the reviews."""
    all_sentences = []

    # Collect all sentences from positive and negative reviews
    for review in reviews:
        review_text = (review['positive'] if review['positive'] else '') + ' ' + (review['negative'] if review['negative'] else '')
        
        if review_text.strip():  # Only process non-empty reviews
            # Use TextBlob to break the review into sentences
            blob = TextBlob(review_text)
            for sentence in blob.sentences:
                # Append each sentence with its sentiment polarity to rank them later
                all_sentences.append({
                    'sentence': str(sentence),
                    'polarity': sentence.sentiment.polarity
                })
    
    # Sort sentences by polarity (positive first)
    sorted_sentences = sorted(all_sentences, key=lambda x: x['polarity'], reverse=True)
    
    # Choose top 5 positive sentences for the summary
    top_sentences = sorted_sentences[:5]

    # Join these sentences into the final summary
    summarized_text = " ".join([sentence['sentence'] for sentence in top_sentences])

    # If no sentences with positive sentiment were found, return a default message
    return summarized_text if summarized_text else "No significant reviews found."





@app.route('/summarize_reviews', methods=['GET'])
def summarize_reviews_route():
    try:
        reviews = get_reviews_from_db(limit=100)
        if not reviews:
            return jsonify({"error": "No reviews found"}), 400
        
        summarized_text = summarize_reviews(reviews)
        return jsonify({"summary": summarized_text}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Route to add review (POST request)
@app.route('/add_review', methods=['POST'])
def add_review():
    if request.content_type == "application/json":
        data = request.get_json()
    else:
        data = request.form

    review_text = data.get("review")
    if not review_text:
        return jsonify({"error": "Review is required"}), 400
    
    try:
        sentiment = get_sentiment(review_text)
        add_review_to_db(sentiment, review_text)
        return jsonify({"message": "Review added successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
