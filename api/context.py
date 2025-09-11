from flask import make_response

from database import db
import log
import models


def add_context(context_elem):
    try:
        new_context = models.Context(context_elem)
        db.session.add(new_context)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.write(msg=f"Failed to create context record", extra_info=str(e), level=log.warning)
        return make_response("Failed to add context", 400)
    return make_response("success", 200)

def edit_context(context_elem):
    existing_context = db.session.execute(
        db.Select(models.Context)
        .where(models.Context.id == context_elem["id"])
    ).scalar_one_or_none()
    if existing_context is None:
        log.write(msg=f"Context {context_elem['id']} doesn't exist",
                  extra_info=f"User {context_elem['author']} tried to edit context {context_elem['id']} but it doesn't exist",
                  level=log.info)
        return make_response("Context doesn't exist", 404)
    
    existing_context.update(context_elem)
    return make_response("success", 200)

def delete_context(context_id):
    existing_context = db.session.execute(
        db.Select(models.Context)
        .where(models.Context.id == context_id)
    ).scalar_one_or_none()
    if existing_context is None:
        log.write(msg=f"Context {context_id} doesn't exist",
                  extra_info=f"Context {context_id} doesn't exist but someone is trying to delete it",
                  level=log.info)
        return make_response("Context doesn't exist", 404)
    
    existing_context.deleted = True
    db.session.commit()
    return make_response("success", 200)

def view_all():
    result = db.session.execute(db.Select(models.Context).where(models.Context.deleted.is_(False))).scalars().all()
    return [x.to_dict() for x in result]