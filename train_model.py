import pandas as pd
import sqlite3
import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def train_and_save_model():
    # Step 1: Database se data load karo
    print("Database se connect kiya ja raha hai...")
    conn = sqlite3.connect('career_guide.db')
    courses_df = pd.read_sql_query("SELECT * FROM courses", conn)
    conn.close()
    print("Courses ka data safaltapurvak load ho gaya hai.")

    # Step 2: Skills ke text ko saaf karo (agar koi value missing hai to)
    courses_df['skills_required'] = courses_df['skills_required'].fillna('')

    # Step 3: TF-IDF Vectorizer ka upyog karke text ko numbers mein badlo
    # TF-IDF har 'skill' ko uski importance ke hisab se ek number deta hai.
    print("Skills ko numerical vectors mein badla ja raha hai...")
    vectorizer = TfidfVectorizer(stop_words='english')
    tfidf_matrix = vectorizer.fit_transform(courses_df['skills_required'])
    print("Vectorization pura hua.")

    # Step 4: Cosine Similarity calculate karo
    # Yeh har course ki doosre sabhi course se similarity ka ek score banata hai.
    print("Courses ke beech similarity calculate ki ja rahi hai...")
    cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)
    print("Similarity calculation pura hua.")

    # Step 5: Trained model aur data ko files mein save karo
    # Hum vectorizer, similarity matrix, aur courses DataFrame ko save karenge.
    print("Model aur data ko files mein save kiya ja raha hai...")
    pickle.dump(vectorizer, open('models/vectorizer.pkl', 'wb'))
    pickle.dump(cosine_sim, open('models/cosine_sim.pkl', 'wb'))
    pickle.dump(courses_df, open('models/courses_df.pkl', 'wb'))
    print("Model safaltapurvak 'models' folder mein save ho gaya hai!")


if __name__ == '__main__':
    train_and_save_model()