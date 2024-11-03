ALLOWED_EXTENSIONS = {'png', 'jpg'}

def allowed_file(picture):
    
    return True if picture.mimetype == 'image/png' else False
