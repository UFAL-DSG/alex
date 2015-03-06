import urllib2


def get_token(cfg):
    token_url = cfg['General'].get('token_url')
    curr_session = cfg['Logging']['session_logger'].session_dir_name.value
    if token_url is not None:
        f_token = urllib2.urlopen(token_url.format(curr_session))
        return f_token.read()
    else:
        raise Exception("Please configure the 'token_url' DM parameter in config.")
