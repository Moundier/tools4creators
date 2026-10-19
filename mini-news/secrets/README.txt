PRIVATE: never share or upload this folder (only this README is tracked by git).

Claude (writes the posts): no file here. It uses Claude Code (`claude`), already logged in to your account.

x.json  (X / Twitter)
  1. developer.x.com -> create a Project + App.
  2. App settings -> "User authentication settings": App permissions = "Read and write".
  3. "Keys and tokens" tab: copy the API Key + Secret, then generate the Access Token + Secret
     (generate them AFTER setting "Read and write", or they stay read-only).
  {"api_key": "...", "api_secret": "...", "access_token": "...", "access_token_secret": "..."}
  Check your X API plan's posting limits in the developer portal.

facebook.json  (a Facebook Page, not your personal profile)
  1. developers.facebook.com -> create an app (type: Business).
  2. Graph API Explorer: choose the app, add pages_manage_posts, pages_read_engagement, pages_show_list,
     generate a user token, then exchange it for a long-lived one (Access Token Debugger -> "Extend").
  3. GET /me/accounts with that token: copy your Page's "id" and "access_token" (a Page token made from a
     long-lived user token doesn't expire).
  {"page_id": "...", "page_token": "..."}
