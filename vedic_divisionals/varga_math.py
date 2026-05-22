
class VargaMath:
    @staticmethod
    def sign_index(lon):
        return int(lon // 30)

    @staticmethod
    def deg_in_sign(lon):
        return lon % 30
