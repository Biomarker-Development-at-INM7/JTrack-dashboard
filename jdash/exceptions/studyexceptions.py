class EmptyStudyTableException(BaseException):
    """
    Exception if study data table is empty resulting in "No data available".
    """
    pass


class StudyAlreadyExistsException(BaseException):
    """
    Exception if the study folder already exists
    """
    def __init__(self,  message="Study folder already exists"):
        self.message = message
        super().__init__(self.message)


class StudyCsvMissingException(BaseException):
    """
    Exception if there is no csv file which contains enrolled subjects information
    """
    pass

