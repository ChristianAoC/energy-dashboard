from flask import make_response

from database import db
import log
import models


def add_context(contextElem):
    try:
        new_context = models.Context(contextElem)
        db.session.add(new_context)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.write(msg=f"Failed to create context record", extra_info=str(e), level=log.warning)
        return make_response("Failed to add context", 400)
    return make_response("success", 200)

def edit_context(contextElem):
    existing_context = db.session.execute(
        db.Select(models.Context)
        .where(models.Context.id == contextElem["id"])
    ).scalar_one_or_none()
    if existing_context is None:
        log.write(msg=f"Context {contextElem['id']} doesn't exist",
                  extra_info=f"User {contextElem['author']} tried to edit context {contextElem['id']} but it doesn't exist",
                  level=log.info)
        return make_response("Context doesn't exist", 404)
    
    existing_context.update(contextElem)
    return make_response("success", 200)

def delete_context(contextID):
    existing_context = db.session.execute(
        db.Select(models.Context)
        .where(models.Context.id == contextID)
    ).scalar_one_or_none()
    if existing_context is None:
        log.write(msg=f"Context {contextID} doesn't exist",
                  extra_info=f"Context {contextID} doesn't exist but someone is trying to delete it",
                  level=log.info)
        return make_response("Context doesn't exist", 404)
    
    existing_context.deleted = True
    db.session.commit()
    return make_response("success", 200)

def view_all():
    result = db.session.execute(db.Select(models.Context).where(models.Context.deleted.is_(False))).scalars().all()
    return [x.to_dict() for x in result]