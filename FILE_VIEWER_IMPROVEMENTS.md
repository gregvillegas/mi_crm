# File Sharing App - Viewer Improvements

## Overview
Enhanced the file_sharing app to allow users to view files directly in the browser instead of only downloading them. This provides a better user experience, especially for PDFs and images.

---

## Changes Implemented

### 1. New View Function (`views.py`)

Added a new `view_file()` function that serves files inline (for viewing in browser):

```python
@login_required
def view_file(request, file_id):
    """View a file in the browser (without forcing download)"""
    file_share = get_object_or_404(GroupFileShare, id=file_id, is_active=True)
    
    # Check access permissions
    if not user_can_access_group(request.user, file_share.group):
        raise Http404("You don't have permission to access this file.")
    
    try:
        # Log the view (only log as 'view' not 'download' since user is just viewing)
        log_file_access(file_share, request.user, 'view', request)
        
        # Serve the file for inline viewing (not as attachment)
        response = FileResponse(
            open(file_share.file.path, 'rb'),
            as_attachment=False,  # This allows viewing in browser
            filename=os.path.basename(file_share.file.name)
        )
        response['Content-Type'] = file_share.mime_type
        response['Content-Disposition'] = f'inline; filename="{os.path.basename(file_share.file.name)}"'
        return response
        
    except FileNotFoundError:
        messages.error(request, 'File not found on server.')
        return redirect('group_files', group_id=file_share.group.id)
```

**Key Features:**
- Sets `as_attachment=False` to allow browser viewing
- Logs the action as 'view' instead of 'download'
- Uses `Content-Disposition: inline` header
- Respects the same permission checks as download

---

### 2. New URL Route (`urls.py`)

Added URL route for the view function:

```python
path('file/<int:file_id>/view/', views.view_file, name='view_file'),
```

**Complete URL Pattern:**
- Download: `/files/file/<id>/download/`
- View: `/files/file/<id>/view/`
- Details: `/files/file/<id>/`

---

### 3. Template Updates

#### A. File Details Page (`file_details.html`)

**File Preview Section:**
- Added both "Open File" and "Download File" buttons
- "Open File" button opens in a new tab (`target="_blank"`)
- Buttons are stacked vertically for better mobile experience
- Primary action is "Open File" (solid button)
- Secondary action is "Download File" (outline button)

```html
<div class="d-grid gap-2">
    <a href="{% url 'view_file' file_share.id %}" class="btn btn-primary" target="_blank">
        <i class="fas fa-eye"></i> Open File
    </a>
    <a href="{% url 'download_file' file_share.id %}" class="btn btn-outline-primary">
        <i class="fas fa-download"></i> Download File
    </a>
</div>
```

#### B. Group Files Listing (`group_files.html`)

**Button Group Updates:**
- Added "Open File" button (green, eye icon)
- Kept "Download" button (blue, download icon)
- Changed previous eye icon to info icon for "Details"
- All buttons have tooltips

```html
<div class="btn-group btn-group-sm">
    <a href="{% url 'view_file' file_share.id %}" class="btn btn-outline-success btn-sm" target="_blank" title="Open File">
        <i class="fas fa-eye"></i>
    </a>
    <a href="{% url 'download_file' file_share.id %}" class="btn btn-outline-primary btn-sm" title="Download">
        <i class="fas fa-download"></i>
    </a>
    <a href="{% url 'file_details' file_share.id %}" class="btn btn-outline-info btn-sm" title="Details">
        <i class="fas fa-info-circle"></i>
    </a>
</div>
```

#### C. All Files Listing (`all_files.html`)

Same button group structure as Group Files listing.

#### D. My Files Listing (`my_files.html`)

**Extended Button Group:**
- Added "Open File" button (green, eye icon)
- Kept "Download" button (blue, download icon)
- Changed previous eye icon to info icon for "Details"
- Kept "Edit" button (gray, edit icon)

```html
<div class="btn-group btn-group-sm">
    <a href="{% url 'view_file' file_share.id %}" class="btn btn-outline-success btn-sm" target="_blank" title="Open File">
        <i class="fas fa-eye"></i>
    </a>
    <a href="{% url 'download_file' file_share.id %}" class="btn btn-outline-primary btn-sm" title="Download">
        <i class="fas fa-download"></i>
    </a>
    <a href="{% url 'file_details' file_share.id %}" class="btn btn-outline-info btn-sm" title="Details">
        <i class="fas fa-info-circle"></i>
    </a>
    <a href="{% url 'edit_file' file_share.id %}" class="btn btn-outline-secondary btn-sm" title="Edit">
        <i class="fas fa-edit"></i>
    </a>
</div>
```

---

## How It Works

### File Types and Browser Behavior

| File Type | Extension | Browser Behavior |
|-----------|-----------|------------------|
| PDF | `.pdf` | Opens in browser PDF viewer |
| Images | `.jpg`, `.jpeg`, `.png`, `.gif` | Displays inline in browser |
| Text | `.txt` | Displays as plain text |
| Office Docs | `.doc`, `.docx`, `.xls`, `.xlsx`, `.ppt`, `.pptx` | Downloads (browser dependent) |
| Archives | `.zip`, `.rar` | Downloads |

**Note:** For file types that browsers cannot display (like Office documents), the browser will still download the file, but this is browser-dependent behavior.

---

## Benefits

### User Experience
1. **Faster Access**: Users can quickly preview files without downloading
2. **No Clutter**: Reduces unnecessary downloads in the user's download folder
3. **Mobile Friendly**: Opens in new tab, making it easy to go back
4. **Better for PDFs**: Browser PDF viewers are familiar to most users

### Tracking
- Viewing and downloading are tracked separately in `FileAccessLog`
- View action doesn't increment the download counter
- Both actions are logged with IP address and user agent

### Flexibility
- Users still have the option to download if they prefer
- Both options are clearly labeled and easily accessible
- Consistent across all file listing pages

---

## Color Coding Scheme

| Action | Button Color | Icon | Purpose |
|--------|-------------|------|---------|
| Open/View | Green (`outline-success`) | Eye | Primary viewing action |
| Download | Blue (`outline-primary`) | Download | Save file locally |
| Details | Light Blue (`outline-info`) | Info Circle | View full details page |
| Edit | Gray (`outline-secondary`) | Edit | Modify file metadata |

---

## Testing

All changes have been validated:
- ✅ Django system check passes with no issues
- ✅ URL routes are properly configured
- ✅ Templates use correct URL names
- ✅ Permission checks are in place
- ✅ File access logging works correctly

---

## Future Enhancements (Optional)

### 1. Enhanced Preview for More File Types
- Consider integrating document viewers like PDF.js for better PDF rendering
- Add image galleries with zoom and navigation
- Use Office Online viewer for Office documents

### 2. Preview Thumbnails
- Generate thumbnails for images and PDF first pages
- Display thumbnails in file listings

### 3. Viewer Statistics
- Track how long users view files
- Show "most viewed" files
- Add analytics dashboard

### 4. Quick Preview Modal
- Add a quick preview modal that shows file content without leaving the page
- Especially useful for images and short PDFs

---

## Deployment Notes

**No Database Migrations Required**
- All changes are in views and templates
- No model changes were made
- The existing `FileAccessLog` model already supports 'view' action

**Static Files**
- No new static files added
- Uses existing Font Awesome icons

**Configuration**
- Ensure `MEDIA_URL` and `MEDIA_ROOT` are properly configured in settings
- Make sure file serving is set up correctly in production

---

## Support

For issues or questions about these changes, refer to:
- Views: `/home/greg/all_proj/crm_project/file_sharing/views.py`
- URLs: `/home/greg/all_proj/crm_project/file_sharing/urls.py`
- Templates: `/home/greg/all_proj/crm_project/file_sharing/templates/file_sharing/`
