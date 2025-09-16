from flask import jsonify, request
from flask_restful import abort, Resource

from . import db_session
from .portfolio import Portfolio
from .portfolio_TRUE import Portfolio_TRUE
from .users import User
from .reqparse import parser


# def abort_if_books_not_found(b_id):
#     session = db_session.create_session()
#     book = session.query(Products).get(b_id)
#     if not book:
#         abort(404, message=f"Book {b_id} not found")


class DostijeniaResource(Resource):
    def get(self):
        return jsonify({'success': 'OK'})

    def delete(self):
        return jsonify({'success': 'OK'})


class UserResource(Resource):
    def get(self, b_id):
        return jsonify({'success': f'{b_id}'})

    def post(self):
        return jsonify({'success': 'OK'})