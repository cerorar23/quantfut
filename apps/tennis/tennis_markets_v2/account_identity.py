"""Identify reused credentials before assuming that a named account is separate."""
import hmac

def clean(value):return value.strip().strip(chr(34)).strip(chr(39))

def is_shared_key(candidate,shared_values):
 shared=shared_values.get('TENNIS_ODDS_API_KEY') or shared_values.get('ODDS_API_KEY')
 return bool(shared and hmac.compare_digest(clean(candidate),clean(shared)))
