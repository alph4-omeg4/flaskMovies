from flask_restful import Resource


class Home(Resource):
    def get(self):
        return 'Welcome home!'