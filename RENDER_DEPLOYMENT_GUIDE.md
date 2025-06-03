# 🚀 **Render Deployment Guide for PharmaDB Deep-Research Micro-Service**

## 📋 **Prerequisites**
- ✅ Render account (you already have this!)
- ✅ GitHub repository with the microservice code (just pushed!)
- ✅ API keys for required services

---

## 🔧 **Step-by-Step Deployment**

### **1. Create New Web Service on Render**

1. **Login to Render Dashboard:** https://dashboard.render.com/
2. **Click "New +"** → **"Web Service"**
3. **Connect Repository:**
   - Select **"Build and deploy from a Git repository"**
   - Choose your **`PharmaDB-research-agent-autogent`** repository
   - Click **"Connect"**

### **2. Configure Service Settings**

**Basic Settings:**
```
Name: pharmadb-research-microservice
Region: Oregon (US West)
Branch: main
Root Directory: . (leave empty)
Runtime: Python 3
Build Command: pip install -r requirements.txt
Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

**Advanced Settings:**
```
Plan: Starter ($7/month) - sufficient for initial deployment
Auto-Deploy: Yes (enabled)
Health Check Path: /health
```

### **3. Environment Variables Setup**

Add these environment variables in Render dashboard:

| Variable Name | Value | Notes |
|---------------|-------|-------|
| `OPENAI_API_KEY` | `your_openai_api_key` | Required for AI processing |
| `SUPABASE_URL` | `your_supabase_project_url` | Your Supabase project URL |
| `SUPABASE_KEY` | `your_supabase_anon_key` | Supabase anonymous/service key |
| `TAVILY_API_KEY` | `your_tavily_api_key` | For web search functionality |
| `SUPABASE_BUCKET_NAME` | `your_bucket_name` | Default: `research-files` |
| `PYTHON_VERSION` | `3.11.4` | Specify Python version |

**🔐 How to Add Environment Variables:**
1. In your service dashboard, go to **"Environment"** tab
2. Click **"Add Environment Variable"**
3. Enter **Key** and **Value**
4. Click **"Save Changes"**

### **4. Deploy the Service**

1. **Click "Create Web Service"**
2. **Render will automatically:**
   - Clone your repository
   - Install dependencies from `requirements.txt`
   - Start the FastAPI application
   - Assign a public URL

**⏱️ Deployment Time:** 3-5 minutes

---

## 🔍 **Post-Deployment Verification**

### **1. Check Service Health**
Your service will be available at: `https://pharmadb-research-microservice.onrender.com`

**Test endpoints:**
```bash
# Health check
curl https://your-service-url.onrender.com/health

# API documentation
open https://your-service-url.onrender.com/docs

# Root endpoint
curl https://your-service-url.onrender.com/
```

### **2. Test Research Endpoint**
```bash
curl -X POST "https://your-service-url.onrender.com/api/v1/research" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the latest AI advancements in drug discovery?",
    "file_ids": null
  }'
```

---

## 📊 **Expected Response Format**

**Successful Health Check:**
```json
{
  "message": "PharmaDB Deep-Research Micro-Service is operational",
  "status": "operational",
  "timestamp": "2025-06-03T15:30:00Z",
  "version": "1.0.0",
  "services": {
    "supabase": "connected",
    "openai": "configured",
    "tavily": "configured"
  }
}
```

**Successful Research Response:**
```json
{
  "answer": "# AI Advancements in Drug Discovery\n\nRecent developments include...",
  "sources": ["web_search"],
  "processing_time": 12.5,
  "token_usage": 1250
}
```

---

## 🚨 **Common Issues & Solutions**

### **Issue 1: Build Fails**
**Symptoms:** Build logs show package installation errors
**Solution:** 
- Check `requirements.txt` format
- Ensure Python version compatibility
- Add `--upgrade pip` to build command if needed

### **Issue 2: Service Starts but Health Check Fails**
**Symptoms:** Build succeeds but health endpoint returns 500
**Solution:**
- Check environment variables are set correctly
- Verify API keys are valid
- Check service logs for detailed error messages

### **Issue 3: Research Endpoint Times Out**
**Symptoms:** Requests to `/api/v1/research` time out
**Solution:**
- Check if all required environment variables are set
- Verify Supabase and OpenAI connectivity
- Consider upgrading to higher Render plan for more resources

---

## 🔧 **Render-Specific Optimizations**

### **1. Update Dockerfile for Render (Optional)**
If you prefer Docker deployment:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY ./app /app/app

# Expose port (Render will override with $PORT)
EXPOSE 8000

# Start application
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### **2. Add Render-specific Health Checks**
Update `app/main.py` if needed:
```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "render_service": os.getenv("RENDER_SERVICE_NAME", "unknown")
    }
```

---

## 📈 **Monitoring & Maintenance**

### **1. Monitor Service Performance**
- **Render Dashboard:** Monitor CPU, memory, and response times
- **Service Logs:** Check for errors and performance issues
- **Health Checks:** Render automatically monitors `/health` endpoint

### **2. Scaling Considerations**
- **Starter Plan:** Good for development/testing
- **Standard Plan:** Recommended for production use
- **Auto-scaling:** Consider if traffic grows significantly

### **3. Updates & Maintenance**
- **Auto-deploy:** Enabled, so git pushes automatically deploy
- **Manual Deploy:** Available in Render dashboard if needed
- **Rollback:** Easy rollback to previous deployments available

---

## 🎯 **Next Steps After Deployment**

1. **✅ Verify all endpoints work correctly**
2. **✅ Test with real research queries**
3. **✅ Monitor performance and logs**
4. **✅ Set up integration with your main application**
5. **📈 Consider upgrading plan based on usage**

---

## 🆘 **Support & Troubleshooting**

**Render Documentation:** https://render.com/docs  
**Service Logs:** Available in Render dashboard  
**Health Check URL:** `https://your-service-url.onrender.com/health`  
**API Documentation:** `https://your-service-url.onrender.com/docs`

**If you encounter issues:**
1. Check service logs in Render dashboard
2. Verify environment variables are set correctly
3. Test health endpoint first
4. Check API key validity

Your microservice is fully ready for deployment! 🚀 