# BIMUZ API - Postman Collection

Complete Postman collection for BIMUZ API with all endpoints, environment variables, and automated token management.

## 📦 Files

- **BIMUZ_API.postman_collection.json** - Main collection with all API requests
- **BIMUZ_API.postman_environment.json** - Environment variables (base URL, tokens)

## 🚀 Quick Start

### 1. Import Collection and Environment

1. Open Postman
2. Click **Import** button (top left)
3. Drag and drop both files:
   - `BIMUZ_API.postman_collection.json`
   - `BIMUZ_API.postman_environment.json`
4. Or click **Upload Files** and select both files

### 2. Select Environment

1. In the top right corner, click the environment dropdown
2. Select **"BIMUZ API - Local"**
3. Update `base_url` if your server is running on a different host/port

### 3. Start Testing

1. First, use **Employee Registration** or **Employee Login** to get tokens
2. Tokens will be automatically saved to environment variables
3. All authenticated requests will use the saved tokens automatically

## 📁 Collection Structure

```
BIMUZ API
├── Authentication
│   ├── Employee Registration (POST)
│   ├── Employee Login (POST)
│   └── Token Refresh (POST)
└── Employee Profile
    ├── Get Profile (GET)
    ├── Update Profile (PATCH) - JSON format
    └── Update Profile (with Avatar) (PATCH) - multipart/form-data
```

## 🔑 Environment Variables

The collection uses the following environment variables:

| Variable | Description | Default Value |
|----------|-------------|---------------|
| `base_url` | API base URL | `http://localhost:8000` |
| `access_token` | JWT access token (auto-saved) | Empty |
| `refresh_token` | JWT refresh token (auto-saved) | Empty |
| `employee_id` | Current employee ID (auto-saved) | Empty |

### Updating Environment Variables

1. Click on **Environments** (left sidebar)
2. Select **"BIMUZ API - Local"**
3. Edit variables as needed
4. Click **Save**

## 📋 Endpoints

### Authentication Endpoints

#### 1. Employee Registration
- **Method:** POST
- **URL:** `{{base_url}}/api/v1/auth/register/`
- **Auth:** Not required
- **Description:** Register a new employee account
- **Auto-saves:** access_token, refresh_token, employee_id

**Request Body Example:**
```json
{
    "email": "employee@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "password": "SecurePassword123!",
    "password_confirm": "SecurePassword123!",
    "full_name": "John Doe",
    "role": "mentor",
    "speciality_id": "revit_architecture",
    "avatar": null
}
```

#### 2. Employee Login
- **Method:** POST
- **URL:** `{{base_url}}/api/v1/auth/login/`
- **Auth:** Not required
- **Description:** Authenticate and get JWT tokens
- **Auto-saves:** access_token, refresh_token, employee_id

**Request Body Example:**
```json
{
    "email": "employee@example.com",
    "password": "SecurePassword123!"
}
```

#### 3. Token Refresh
- **Method:** POST
- **URL:** `{{base_url}}/api/v1/auth/token/refresh/`
- **Auth:** Not required
- **Description:** Get new access token using refresh token
- **Auto-saves:** access_token, refresh_token (if rotation enabled)

**Request Body:**
```json
{
    "refresh": "{{refresh_token}}"
}
```

### Employee Profile Endpoints

#### 4. Get Profile
- **Method:** GET
- **URL:** `{{base_url}}/api/v1/auth/profile/`
- **Auth:** Required (Bearer Token)
- **Description:** Retrieve authenticated employee's profile

#### 5. Update Profile
- **Method:** PATCH
- **URL:** `{{base_url}}/api/v1/auth/profile/`
- **Auth:** Required (Bearer Token)
- **Description:** Update profile (JSON format)
- **Content-Type:** application/json

**Request Body Example:**
```json
{
    "full_name": "John Updated Doe",
    "speciality_id": "revit_structure"
}
```

#### 6. Update Profile (with Avatar)
- **Method:** PATCH
- **URL:** `{{base_url}}/api/v1/auth/profile/`
- **Auth:** Required (Bearer Token)
- **Description:** Update profile with avatar image upload
- **Content-Type:** multipart/form-data

**Form Data:**
- `full_name`: Text (optional)
- `speciality_id`: Text (optional, only for mentors)
- `avatar`: File (optional)

## 🔐 Authentication

All profile endpoints require JWT Bearer authentication:

1. Use **Employee Registration** or **Employee Login** first
2. Tokens are automatically saved to environment variables
3. Subsequent requests use `{{access_token}}` automatically
4. When access token expires (1 hour), use **Token Refresh** to get a new one

### Manual Token Setup

If you need to set tokens manually:

1. Select **"BIMUZ API - Local"** environment
2. Set `access_token` variable to your JWT access token
3. Set `refresh_token` variable to your JWT refresh token

## 🎯 Roles and Specialities

### Available Roles
- `dasturchi` - Developer
- `direktor` - Director
- `administrator` - Administrator
- `sotuv_agenti` - Sales Agent
- `mentor` - Mentor (requires speciality_id)
- `assistent` - Assistant

### Available Specialities (for Mentors only)
- `revit_architecture` - Revit Architecture
- `revit_structure` - Revit Structure
- `tekla_structure` - Tekla Structure

**Note:** `speciality_id` is **required** for `mentor` role and **must not be set** for other roles.

## ✅ Features

### Automated Token Management
- Tokens are automatically saved after login/registration
- Token refresh automatically updates environment variables
- All authenticated requests use saved tokens

### Pre-configured Requests
- All endpoints are pre-configured with example data
- Detailed descriptions for each endpoint
- Proper headers and authentication setup

### Test Scripts
- Automatic token extraction and saving
- Console logging for debugging
- Error handling

## 📝 Usage Tips

1. **Start with Authentication**
   - Always register or login first to get tokens
   - Tokens are valid for 1 hour (access) and 7 days (refresh)

2. **Token Refresh**
   - Use Token Refresh when access token expires
   - Refresh tokens are automatically rotated (if enabled)

3. **Profile Updates**
   - Use JSON format for text-only updates
   - Use multipart/form-data format for avatar uploads

4. **Environment Switching**
   - Create new environments for different servers (dev, staging, prod)
   - Duplicate "BIMUZ API - Local" and update `base_url`

5. **Testing Workflow**
   ```
   1. Employee Registration/Login → Get tokens
   2. Get Profile → Verify authentication
   3. Update Profile → Test updates
   4. Token Refresh → Test token refresh (optional)
   ```

## 🔧 Troubleshooting

### Tokens not saving
- Check that test scripts are enabled (Collection → Edit → Tests)
- Verify environment is selected
- Check Postman console for errors

### Authentication errors
- Verify tokens are saved in environment
- Check token expiration (access tokens expire after 1 hour)
- Use Token Refresh to get new tokens

### Connection errors
- Verify `base_url` is correct
- Ensure server is running
- Check CORS settings if accessing from different origin

### Validation errors
- Check required fields are provided
- Verify role/speciality combinations:
  - Mentors **must** have `speciality_id`
  - Non-mentors **must not** have `speciality_id`
- Check password requirements (min 8 chars, strong validation)

## 📚 Additional Resources

- **API Documentation (Text):** `api_docs.txt`
- **API Documentation (YAML):** `api_docs.yml`
- **Swagger UI:** `http://localhost:8000/swagger/`
- **ReDoc:** `http://localhost:8000/redoc/`

## 📄 Response Format

All responses follow this format:

**Success:**
```json
{
    "success": true,
    "message": "Operation successful",
    "data": { ... }
}
```

**Error:**
```json
{
    "success": false,
    "message": "Error message",
    "errors": { ... }
}
```

## 🆘 Support

For issues or questions:
- Check API documentation files
- Review Swagger/ReDoc documentation
- Check server logs for detailed error messages

---

**Last Updated:** 2026-01-11  
**API Version:** 1.0  
**Collection Version:** 1.0