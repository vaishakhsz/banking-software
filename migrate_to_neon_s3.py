import os
import re
import time
import urllib.parse
import psycopg2
import boto3
from dotenv import load_dotenv

# Load local environment variables from .env if present
load_dotenv()

# S3 Configuration
S3_ENDPOINT = "https://br-shiny-band-ayqa8iag.storage.c-5.us-east-2.aws.neon.tech"
S3_ACCESS_KEY = "nak_live_6f21918c7bdb46bc99e95b1091ed7f98"
S3_SECRET_KEY = "nsk_live_f39392f340cade411455670348dd4cd187fa13abd5c80d833ca2437e4df8579b"
S3_BUCKET = "assets"
UPLOAD_DIR = "customer_uploads"

# Database connection parsing
def parse_postgres_conn_info(raw_url):
    if not raw_url:
        return None
    try:
        pattern = r'^(?:postgresql|postgres):\/\/(?:([^:]+):?(.*)@)?([^:\/\?]+)(?::(\d+))?(?:\/([^?]*))?(?:\?(.*))?$'
        match = re.match(pattern, raw_url)
        if match:
            user = match.group(1) or "postgres"
            password = match.group(2) or ""
            host = match.group(3)
            port = int(match.group(4)) if match.group(4) else 5432
            dbname = match.group(5) or "postgres"
            return {
                "host": host,
                "port": port,
                "user": urllib.parse.unquote(user),
                "password": urllib.parse.unquote(password),
                "dbname": dbname,
                "sslmode": "require"
            }
    except Exception as e:
        print(f"Error parsing database URL: {e}")
    return None

def migrate():
    # Get Database URL
    db_url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_URL") or os.getenv("POSTGRES_URL")
    if not db_url:
        # Prompt user if not found in environment
        db_url = input("Enter your Neon PostgreSQL connection string (DATABASE_URL): ").strip()
    
    params = parse_postgres_conn_info(db_url)
    if not params:
        print("❌ Invalid database connection URL. Exiting.")
        return
        
    print("⏳ Connecting to Neon database...")
    try:
        conn = psycopg2.connect(**params)
        cursor = conn.cursor()
        print("✅ Connected to Neon database successfully.")
    except Exception as e:
        print(f"❌ Failed to connect to Neon database: {e}")
        return

    print("⏳ Initializing Neon Object Storage S3 Client...")
    try:
        s3 = boto3.client(
            's3',
            endpoint_url=S3_ENDPOINT,
            aws_access_key_id=S3_ACCESS_KEY,
            aws_secret_access_key=S3_SECRET_KEY,
            region_name='us-east-2'
        )
        print("✅ Neon Storage S3 Client initialized successfully.")
    except Exception as e:
        print(f"❌ Failed to initialize S3 client: {e}")
        conn.close()
        return

    # Fetch all customers
    cursor.execute("SELECT id, name, adhar_file, pan_file, signature_file FROM customers")
    customers = cursor.fetchall()
    
    if not customers:
        print("ℹ️ No customers found in the database. Exiting.")
        conn.close()
        return

    print(f"📋 Found {len(customers)} customers. Starting migration...")
    
    migrated_count = 0
    errors_count = 0

    for cust in customers:
        cust_id, name, adhar, pan, sig = cust
        print(f"\n👤 Processing Customer ID {cust_id} ({name}):")
        
        updates = {}
        for col_name, file_path in [("adhar_file", adhar), ("pan_file", pan), ("signature_file", sig)]:
            if not file_path:
                continue
                
            # If it's already an S3 key (doesn't start with UPLOAD_DIR or look like a local path)
            if not (file_path.startswith(UPLOAD_DIR) or "/" in file_path or "\\" in file_path or os.path.exists(file_path)):
                print(f"  - {col_name} already appears to be an S3 key: {file_path}")
                continue
                
            filename = os.path.basename(file_path)
            local_locations = [
                file_path,
                os.path.join(UPLOAD_DIR, filename),
                os.path.join(os.getcwd(), UPLOAD_DIR, filename)
            ]
            
            found_local_path = None
            for loc in local_locations:
                if os.path.exists(loc):
                    found_local_path = loc
                    break
                    
            if not found_local_path:
                print(f"  ❌ Local file not found for {col_name}: expected at '{file_path}' or in '{UPLOAD_DIR}/'")
                errors_count += 1
                continue
                
            # Define new unique S3 key
            unique_key = f"{int(time.time())}_{filename}"
            print(f"  ⏳ Uploading {filename} ➔ S3 bucket '{S3_BUCKET}' as '{unique_key}'...")
            
            try:
                # Get Content Type
                content_type = "application/octet-stream"
                if filename.lower().endswith((".jpg", ".jpeg")):
                    content_type = "image/jpeg"
                elif filename.lower().endswith(".png"):
                    content_type = "image/png"
                elif filename.lower().endswith(".pdf"):
                    content_type = "application/pdf"
                    
                with open(found_local_path, "rb") as f_s3:
                    s3.put_object(
                        Bucket=S3_BUCKET,
                        Key=unique_key,
                        Body=f_s3,
                        ContentType=content_type
                    )
                
                updates[col_name] = unique_key
                print(f"  ✅ Uploaded successfully.")
                migrated_count += 1
                time.sleep(0.1) # Small delay to avoid rate limit spikes
            except Exception as upload_err:
                print(f"  ❌ Upload failed: {upload_err}")
                errors_count += 1
                
        if updates:
            # Update database
            set_clause = ", ".join(f"{col} = %s" for col in updates.keys())
            update_params = list(updates.values()) + [cust_id]
            try:
                cursor.execute(f"UPDATE customers SET {set_clause} WHERE id = %s", update_params)
                conn.commit()
                print(f"  💾 Database updated successfully with S3 keys.")
            except Exception as db_err:
                conn.rollback()
                print(f"  ❌ Database update failed: {db_err}")
                errors_count += len(updates)
                
    conn.close()
    print("\n==================================================")
    print("🎉 MIGRATION COMPLETED")
    print(f"✅ Successful uploads: {migrated_count}")
    print(f"❌ Failed/Missing files: {errors_count}")
    print("==================================================")

if __name__ == "__main__":
    migrate()
