# 🚀 Quick Start - Web Demo in 60 Seconds

## Test Locally Right Now

```bash
# 1. Install Flask (one time only)
pip install Flask

# 2. Go to the web_demo folder
cd web_demo

# 3. Run the demo
python app.py
```

**Open your browser:** http://localhost:5000

**Click:** "Run Analysis" button

**Watch:** Results appear showing $1M+ recovery potential!

---

## What You'll See

### 1. Dashboard Stats
- 214 claims processed
- 212 alerts generated  
- 131 high-priority alerts
- **$1,021,704 total potential recovery**

### 2. Alert Distribution
Visual breakdown of 7 COB issue types:
- Auto Liability: 11 alerts
- Workers Comp: 10 alerts
- MSP Violations: 43 alerts
- And more...

### 3. Top 10 High-Value Alerts
Detailed cards showing:
- Patient info (name, age, ID)
- Recovery amount ($71K, $50K, etc.)
- Confidence score (85-95%)
- Specific issue description
- Recommended action

### 4. Red Flag Accounts Table
15 patients with highest recovery potential:
- Michael Moore: $179K across 3 alerts
- Lisa Thomas: $172K across 3 alerts
- Nancy Thompson: $110K across 2 alerts

---

## Share with Clients (5-Minute Deploy)

### Deploy to Render.com (Free):

1. **Create account:** https://render.com
2. **New Web Service** → Connect GitHub repo
3. **Settings:**
   - Build: `pip install -r requirements.txt`
   - Start: `python app.py`
4. **Deploy!**

**Your live demo URL:** `https://your-app.onrender.com`

Send this link to clients - they just click and see results!

---

## During Client Meetings

### Screen Share Flow:
1. Open demo URL
2. Say: "Watch our agent analyze 100 patients..."
3. Click "Run Analysis"
4. Results appear in 1-2 seconds
5. Walk through the stats and top alerts

### Key Talking Points:
- "Identified 212 COB issues in under a second"
- "This top alert shows $71K from a car accident billed wrong"
- "85-95% confidence scores on detection"
- "5 red flag accounts = $562K immediate recovery"

---

## Troubleshooting

**"Module not found" error?**
```bash
pip install Flask
```

**"Port already in use"?**
```bash
# Change port in app.py (last line):
app.run(debug=True, host='0.0.0.0', port=5001)
```

**Demo not loading in browser?**
- Make sure you see "Running on http://0.0.0.0:5000"
- Try: http://127.0.0.1:5000 instead

---

## Next Steps

✅ Test locally now (60 seconds)  
✅ Deploy to Render (5 minutes)  
✅ Share link with first client  
✅ Customize colors/branding if desired  

**You're ready to demo!** 🎉
