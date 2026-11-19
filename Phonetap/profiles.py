import importlib.util
import json
import os
import sys

profile_fields = (
    'username',
    'password',
    'local',
    'host',
    'port',
    'directories',
    'extensions')

PROFILES_FILENAME = 'profiles.json'


def _is_venv_dir(path):
    return os.path.isfile(os.path.join(path, 'pyvenv.cfg'))


def _find_in_dir(directory):
    candidate = os.path.join(directory, PROFILES_FILENAME)
    return candidate if os.path.isfile(candidate) else None


def _find_below_python_root():
    # If running inside a virtual environment, search the base interpreter
    # installation instead, and make sure the venv itself is skipped.
    venv_dir = sys.prefix if sys.prefix != sys.base_prefix else None
    root = sys.base_prefix

    for dirpath, dirnames, filenames in os.walk(root):
        if venv_dir and os.path.abspath(dirpath) == os.path.abspath(venv_dir):
            dirnames[:] = []
            continue
        dirnames[:] = [d for d in dirnames if not _is_venv_dir(os.path.join(dirpath, d))]
        if PROFILES_FILENAME in filenames:
            return os.path.join(dirpath, PROFILES_FILENAME)
    return None


def _find_in_package_dir():
    package_name = (__package__ or '').split('.')[0]
    if not package_name:
        return None
    try:
        spec = importlib.util.find_spec(package_name)
    except (ImportError, ValueError):
        return None
    if not spec or not spec.origin:
        return None
    package_dir = os.path.dirname(spec.origin)
    return _find_in_dir(package_dir)


def _find_profiles_file():
    script_dir = os.path.dirname(os.path.abspath(sys.argv[0])) if sys.argv and sys.argv[0] else None
    locations = (
        lambda: _find_in_dir(os.getcwd()),
        lambda: _find_in_dir(os.path.expanduser('~')),
        lambda: _find_in_dir(script_dir) if script_dir else None,
        _find_below_python_root,
        _find_in_package_dir,
    )
    for find in locations:
        found = find()
        if found:
            return found
    return None


def resolve_profile(profile_file):
    if profile_file is None:
        profile_file = _find_profiles_file()
    if profile_file is None:
        raise ValueError("profile file couldn't be found")
    print(f'Using profile file in {profile_file}.')
    return profile_file


def _find_profile_key(profiles, profile_name):
    """Return the actual key in profiles matching profile_name case-insensitively, or None."""
    if profile_name is None:
        return None
    lowered = profile_name.lower()
    return next((key for key in profiles if key.lower() == lowered), None)


def _explode_profile(**kwargs):
    print('explode profile')
    profile_file = resolve_profile(kwargs.get('profile_file'))
    profile_name = kwargs['profile']

    if os.path.exists(profile_file):
        with open(profile_file) as j:
            profiles = json.loads(j.read())
    else:
        missing_fields = [fi for fi in profile_fields + ['profile'] if not bool(kwargs[fi])]
        if any(missing_fields):
            print(f'On profile creation, all fields are required. {', '.join(missing_fields)} are missing.')
        profiles = {}

    if profile_name:
        existing_key = _find_profile_key(profiles, profile_name)
        saved_profile = profiles.get(existing_key, {})
    else:
        saved_profile = next(profiles.values(), {})

    profile = {fi: kwargs.get(fi) or saved_profile.get(fi) for fi in profile_fields}
    profile['profile'] = profile_name
    profile['profile_file'] = profile_file
    add_directories = kwargs['add_directories']
    remove_directories = kwargs['remove_directories']
    if not kwargs['directories']:
        profile['directories'] = list(
            set(profile['directories'])
            .union(add_directories if add_directories else [])
            .difference(remove_directories if remove_directories else []))
    add_extensions = kwargs['add_extensions']
    remove_extensions = kwargs['remove_extensions']
    if not kwargs['extensions']:
        profile['extensions'] = list(
            set(profile['extensions'])
            .union(add_extensions if add_extensions else [])
            .difference(remove_extensions if remove_extensions else []))
    print(json.dumps(profile, indent=4))
    return profile


def explode_profile(**kwargs):
    profile = _explode_profile(**kwargs)
    return (profile[fi] for fi in profile_fields)


def edit(**kwargs):
    profile = _explode_profile(**kwargs)
    profile_file = resolve_profile(profile['profile_file'])
    with open(profile_file, 'r') as j:
        profiles = json.loads(j.read())
    existing_key = _find_profile_key(profiles, profile['profile'])
    profiles[existing_key if existing_key else profile['profile']] = profile
    with open(profile_file, 'w') as j:
        dumps = json.dumps(profiles, indent=2)
        j.write(dumps)


def list_profiles(profile_file):
    profile_file = resolve_profile(profile_file)
    with open(profile_file, 'r') as j:
        profiles = json.loads(j.read())
    print(f'Available profiles are :{profiles.keys()}')


def show(profile_file, profile=None):
    profile_file = resolve_profile(profile_file)
    with open(profile_file, 'r') as j:
        profiles = json.loads(j.read())
    if profile:
        existing_key = _find_profile_key(profiles, profile)
        print(json.dumps(profiles.get(existing_key, {}), indent=2))
    else:
        # list_profiles()
        print(f'Available profiles are :{profiles.keys()}')
