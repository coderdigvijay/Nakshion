# Python 3.14 Compatibility Issues

## bcrypt + passlib
- `passlib` doesn't support `bcrypt>=5.0` — crashes with `AttributeError: module 'bcrypt' has no attribute '__about__'`
- **Fix:** Pin `bcrypt==4.1.3` in requirements.txt
- The warning still appears in logs but hashing works correctly

## greenlet
- SQLAlchemy async requires `greenlet` package on Python 3.14
- Error: `ValueError: the greenlet library is required to use this function`
- **Fix:** `pip install greenlet`

## email-validator
- Pydantic's `EmailStr` type requires `email-validator` package
- Not installed by default with pydantic
- **Fix:** `pip install email-validator`
