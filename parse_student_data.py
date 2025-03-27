import csv
import psycopg2
import os
import boto3
from dotenv import load_dotenv
from io import StringIO

# Load environment variables
load_dotenv()

def db_connect():
    """Establishes a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT")
        )
        return conn
    except psycopg2.Error as e:
        print(f"Error connecting to database: {e}")
        return None

def create_table(cursor):
    """Creates the students table if it doesn't exist."""
    create_table_query = """
    CREATE TABLE IF NOT EXISTS students (
        id SERIAL PRIMARY KEY,
        student_id VARCHAR(10),
        name VARCHAR(100) NOT NULL,
        age VARCHAR(3),
        gender VARCHAR(10),
        grade CHAR(1),
        city VARCHAR(50),
        email VARCHAR(50),
        phone_number VARCHAR(15),
        enrollment_date VARCHAR(15),
        subjects TEXT
    );
    """
    cursor.execute(create_table_query)

def insert_records(cursor, reader):
    """Inserts student records into the database."""
    insert_query = """
    INSERT INTO students (student_id, name, age, gender, grade, city, email, phone_number, enrollment_date, subjects)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
    """
    
    for row in reader:
        
        if len(row) != 10:
            print(f"Skipping row due to incorrect column count: {row}")
            continue

        row = [value.strip() if isinstance(value, str) else value for value in row]

        try:
            cursor.execute(insert_query, row)
        except psycopg2.Error as e:
            print(f"Error inserting row {row}: {e}")

def get_latest_csv_from_s3(bucket_name):
    """Lists files in an S3 bucket and returns the latest CSV file path."""
    s3 = boto3.client('s3')

    try:
        response = s3.list_objects_v2(Bucket=bucket_name)
        if "Contents" not in response:
            print("No files found in bucket.")
            return None

        # Filter CSV files and sort by last modified date
        csv_files = [obj for obj in response["Contents"] if obj["Key"].endswith(".csv")]
        if not csv_files:
            print("No CSV files found in the bucket.")
            return None
        
        latest_file = max(csv_files, key=lambda x: x["LastModified"])
        print(f"Selected File: {latest_file['Key']}")
        return latest_file["Key"]
    
    except Exception as e:
        print(f"Error listing files in S3: {e}")
        return None
    
def read_csv_from_s3(bucket_name, object_key):
    """Reads a CSV file from an S3 bucket."""
    s3 = boto3.client('s3')

    try:
        response = s3.get_object(Bucket=bucket_name, Key=object_key)
        csv_data = response['Body'].read().decode('utf-8')
        return csv.reader(StringIO(csv_data))
    except Exception as e:
        print(f"Error reading CSV from S3: {e}")
        return None

def main():
    bucket_name = 'choice-school'
    
    # Get the latest CSV file dynamically
    latest_file_key = get_latest_csv_from_s3(bucket_name)
    if not latest_file_key:
        print("No CSV file found in S3.")
        return

    print(f"Downloading latest CSV file: {latest_file_key}")
    reader = read_csv_from_s3(bucket_name, latest_file_key)
    
    if not reader:
        print("Error: Could not read CSV from S3.")
        return
    
    conn = db_connect()
    if not conn:
        return
    
    try:
        with conn:
            with conn.cursor() as cursor:
                create_table(cursor)
                next(reader, None)  # Skip header row
                insert_records(cursor, reader)
                print("Data inserted successfully.")
    except psycopg2.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
