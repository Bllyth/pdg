def check_users_below_supervisor(supervisor_email, pdg_id):
    # users = Get all users with supervisor_id as the supervisor
    users = User.query.filter_by(supervisor=supervisor_email).all()
    for user in users:
        # get pdg matching user.id and pdg_id
        pdg = PDG.query.filter_by(user_id=user.id, id=pdg_id).first()

        if pdg:
            return pdg
        pdg = check_users_below_supervisor(user.email, pdg_id)
        if pdg:
            return pdg
    return None