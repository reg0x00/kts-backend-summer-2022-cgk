from marshmallow import Schema, fields


class QuestionSchema(Schema):
    id = fields.Int(required=False)
    title = fields.Str(required=True)
    answers = fields.Nested("AnswerSchema", many=True, required=True)


class AnswerSchema(Schema):
    title = fields.Str(required=True)



class ListQuestionSchema(Schema):
    questions = fields.Nested(QuestionSchema, many=True)
