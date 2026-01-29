# COB Agent Web Demo - Deployment Guide

## Overview

This is a browser-based demonstration of the Sightline Health COB Agent. Clients can interact with the system through a clean, professional web interface without needing to install Python or run terminal commands.

## What This Demo Shows

- **One-click analysis** of 100 patients with COB scenarios
- **Real-time results** displayed in a modern dashboard
- **Interactive visualizations** of alerts and recovery potential
- **Detailed alert cards** showing specific COB issues
- **Red flag accounts** table for immediate review

---

## Quick Start (Local Testing)

### Prerequisites
- Python 3.9+ installed
- Flask library

### Run Locally in 3 Steps:

```bash
# 1. Install Flask
pip install Flask

# 2. Navigate to web_demo directory
cd web_demo

# 3. Start the server
python app.py
```

**Open in browser:** http://localhost:5000

That's it! Click "Run Analysis" and watch the demo.

---

## Deployment Options

### Option A: Deploy to Render (Free, Easiest)

**Render.com** offers free hosting perfect for demos. Setup takes 5 minutes.

#### Steps:

1. **Create account** at https://render.com (free)

2. **Push your code to GitHub:**
   ```bash
   # Create new repo on GitHub
   # Then push web_demo folder:
   git init
   git add .
   git commit -m "COB Agent Web Demo"
   git remote add origin YOUR_GITHUB_REPO_URL
   git push -u origin main
   ```

3. **Connect Render to GitHub:**
   - Click "New +" → "Web Service"
   - Connect your GitHub repo
   - Select the `web_demo` folder

4. **Configure settings:**
   - **Name:** sightline-cob-demo
   - **Environment:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python app.py`
   - **Plan:** Free

5. **Deploy!**
   - Click "Create Web Service"
   - Wait 2-3 minutes for deployment
   - Your demo will be live at: `https://sightline-cob-demo.onrender.com`

**Pros:**
- ✅ Free forever
- ✅ HTTPS included
- ✅ Auto-deploys from GitHub
- ✅ No credit card required

**Cons:**
- ⚠️ Spins down after 15min of inactivity (30sec cold start)
- ⚠️ Free tier has some limitations

---

### Option B: Deploy to Heroku

**Heroku** is another popular option with a free tier.

#### Additional files needed:

Create `Procfile` in web_demo directory:
```
web: python app.py
```

Create `runtime.txt`:
```
python-3.11.0
```

#### Steps:

```bash
# 1. Install Heroku CLI
# Download from: https://devcenter.heroku.com/articles/heroku-cli

# 2. Login
heroku login

# 3. Create app
heroku create sightline-cob-demo

# 4. Deploy
git push heroku main

# 5. Open
heroku open
```

**Your demo:** `https://sightline-cob-demo.herokuapp.com`

---

### Option C: Deploy to AWS (Most Professional)

For production-grade hosting with custom domain.

#### Using AWS Elastic Beanstalk:

```bash
# 1. Install EB CLI
pip install awsebcli

# 2. Initialize
eb init -p python-3.11 sightline-cob-demo

# 3. Create environment
eb create sightline-demo-env

# 4. Deploy
eb deploy

# 5. Open
eb open
```

#### Cost:
- ~$25/month for t3.micro instance
- Can add custom domain (sightlinedemo.com)
- Professional SSL certificate
- 99.99% uptime SLA

---

### Option D: Deploy to Vercel (Modern, Fast)

**Vercel** specializes in modern web apps with excellent performance.

#### Steps:

1. **Install Vercel CLI:**
   ```bash
   npm install -g vercel
   ```

2. **Deploy:**
   ```bash
   cd web_demo
   vercel
   ```

3. **Answer prompts:**
   - Project name: sightline-cob-demo
   - Framework: Other
   - Build command: `pip install -r requirements.txt`
   - Output directory: (leave blank)

4. **Done!** Your URL: `https://sightline-cob-demo.vercel.app`

**Note:** Vercel works best with Node.js. For Python/Flask, Render is easier.

---

## Custom Domain Setup

Once deployed, you can add a custom domain like `demo.sightlinehealth.com`

### For Render:

1. Go to dashboard → Settings → Custom Domain
2. Add: `demo.sightlinehealth.com`
3. Update DNS with provided CNAME
4. SSL certificate auto-provisioned

### DNS Settings (at your domain registrar):

```
Type: CNAME
Name: demo
Value: sightline-cob-demo.onrender.com
TTL: 3600
```

---

## Customization

### Change Number of Patients:

Edit `app.py`, line 162:
```python
# Default is 100 patients
initialize_demo(100, 42)

# Change to 50:
initialize_demo(50, 42)

# Change to 200:
initialize_demo(200, 42)
```

### Add Your Logo:

1. Add logo image to `web_demo/static/` folder
2. Update `templates/index.html`, line 202:
```html
<h1>
    <img src="/static/logo.png" style="height: 40px; vertical-align: middle;">
    Sightline Health - COB Agent
</h1>
```

### Change Color Scheme:

Edit `templates/index.html` in the `<style>` section:

```css
/* Primary gradient - currently purple */
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);

/* Change to blue: */
background: linear-gradient(135deg, #4299e1 0%, #3182ce 100%);

/* Change to green: */
background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);
```

---

## Sharing with Clients

### Option 1: Direct Link
Simply send them the URL:
```
"Check out our COB Agent demo at:
https://sightline-cob-demo.onrender.com

Click 'Run Analysis' to see it process 100 patients
and identify $1M+ in recovery potential."
```

### Option 2: QR Code
Generate a QR code pointing to your demo URL:
- Use: https://qr-code-generator.com
- Print on business cards or presentation slides
- Clients scan to access instant demo

### Option 3: Embedded in Email
```html
<a href="https://sightline-cob-demo.onrender.com" 
   style="background: #667eea; color: white; padding: 15px 30px; 
          text-decoration: none; border-radius: 8px; font-weight: bold;">
    View Live Demo →
</a>
```

---

## Demo Flow for Client Meetings

### Before Meeting:
1. Open demo URL
2. Test "Run Analysis" button
3. Review results to ensure they load properly

### During Meeting:
1. **Share screen** showing the demo page
2. **Say:** "Let me show you our COB agent analyzing 100 patients..."
3. **Click:** "Run Analysis" button
4. **Watch together** as results populate (1-2 seconds)
5. **Highlight:**
   - Total potential recovery ($1M+)
   - Number of high-priority alerts
   - Top alert details (click to expand)
   - Red flag accounts table

### Key Talking Points:
- "This identified 212 COB issues in under a second"
- "Look at this top alert - $71K recovery from a car accident billed wrong"
- "Notice the confidence scores - 85-95% certainty"
- "These 5 red flag accounts alone represent $562K in recovery"
- "In production, this runs on every claim before submission"

---

## Monitoring & Analytics

### View Access Logs (Render):
```bash
render logs sightline-cob-demo
```

### Add Google Analytics:

Add to `templates/index.html` before `</head>`:
```html
<!-- Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-XXXXXXXXXX');
</script>
```

Track:
- Page views
- Button clicks
- Time spent on demo
- Conversion to contact form

---

## Troubleshooting

### Demo not loading?
```bash
# Check server logs
python app.py

# Should see:
# "Initializing COB Agent Web Demo..."
# "Demo initialized with 100 patients"
# "Running on http://0.0.0.0:5000"
```

### "Run Analysis" button does nothing?
- Check browser console (F12) for JavaScript errors
- Ensure Flask server is running
- Try refreshing the page

### Slow to load?
- Free tier services spin down after inactivity
- First load may take 30-60 seconds (cold start)
- Subsequent loads are instant
- Upgrade to paid tier for always-on hosting

### Can't access from other devices?
- Local dev (localhost:5000) only works on your computer
- Deploy to Render/Heroku for public access

---

## Security Considerations

### For Demo Purposes:
✅ Uses synthetic data only - no PHI
✅ No authentication needed
✅ Safe to share publicly

### For Production:
Would need:
- User authentication (login required)
- Role-based access control
- HIPAA compliance (encrypted data)
- Audit logging
- Private hosting (VPN or allowlist)

---

## Cost Summary

| Option | Setup Time | Monthly Cost | Best For |
|--------|------------|--------------|----------|
| **Render Free** | 5 min | $0 | Quick demos, testing |
| **Heroku Free** | 10 min | $0 | Alternative to Render |
| **AWS EB** | 20 min | $25 | Production, custom domain |
| **Vercel** | 5 min | $0 | Modern stack preference |

**Recommendation for demos:** Start with Render Free, upgrade to AWS when you have paying customers.

---

## Next Steps

1. **Test locally first:** `python app.py` → http://localhost:5000
2. **Deploy to Render:** Follow Option A above (5 minutes)
3. **Share with first client:** Send them the live URL
4. **Iterate based on feedback:** Customize colors, add features
5. **Upgrade when ready:** Move to paid hosting for always-on

---

## Support

**Questions about deployment?**
- Render docs: https://render.com/docs
- Flask docs: https://flask.palletsprojects.com/
- Python docs: https://www.python.org/

**Need help customizing?**
Contact Zack at Sightline Health

---

## Files Included

```
web_demo/
├── app.py                 # Flask backend
├── requirements.txt       # Python dependencies
├── templates/
│   └── index.html        # Web interface
└── DEPLOYMENT_GUIDE.md   # This file
```

---

**You're ready to demo!** The web interface provides a professional, client-ready experience that showcases Sightline's COB detection capabilities without any technical setup for viewers.
