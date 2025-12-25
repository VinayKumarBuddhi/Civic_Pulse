# How to Run Civic Pulse App

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Up MongoDB

#### Option A: Local MongoDB
- Install MongoDB on your system
- Start MongoDB service
- Default connection will be: `mongodb://localhost:27017/`

#### Option B: MongoDB Atlas (Cloud)
- Create a `.env` file in the project root:
```
MONGODB_URI=mongodb+srv://your-username:your-password@your-cluster.mongodb.net/
DATABASE_NAME=civic-pulse
```

### 3. Run the Application

Open terminal/command prompt in the project directory and run:

```bash
streamlit run app.py
```

The app will automatically open in your default web browser at `http://localhost:8501`

## Alternative Run Commands

### Run on a specific port:
```bash
streamlit run app.py --server.port 8502
```

### Run with specific host:
```bash
streamlit run app.py --server.address 0.0.0.0
```

### Run with specific browser:
```bash
streamlit run app.py --server.headless true
```

## Troubleshooting

### MongoDB Connection Error
- Make sure MongoDB is running (if using local MongoDB)
- Check `.env` file if using MongoDB Atlas
- Verify connection string is correct

### Import Errors
- Make sure all dependencies are installed: `pip install -r requirements.txt`
- Check that you're in the correct directory

### Port Already in Use
- Use a different port: `streamlit run app.py --server.port 8502`
- Or stop the existing Streamlit process

## First Time Setup

If this is your first time running the app:
1. Make sure MongoDB is set up and running
2. You may want to run `database/init_db.py` to initialize collections (if needed)
3. The app will work even without data, but you'll see "No NGOs found" until NGOs are added

