import cloudinary
import cloudinary.api

cloudinary.config(
    cloud_name="dvlgdzood",
    api_key="369546975274421",
    api_secret="e_Qk_BECoZhIaBhbr5LCllzS7Ao"
)

# Get all files
print("Fetching all files...")
result = cloudinary.api.resources(max_results=100)

if not result['resources']:
    print("No files found!")
else:
    files = [r['public_id'] for r in result['resources']]
    print(f"Found {len(files)} files")
    
    # Delete them
    print("Deleting...")
    cloudinary.api.delete_resources(files)
    print("✅ All files deleted!") 
