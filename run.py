# import logging
# logging.basicConfig(level=logging.INFO)

# from app import create_app

# app = create_app()

# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=5000, debug=True)

import os
import logging
logging.basicConfig(level=logging.INFO)

from app import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)