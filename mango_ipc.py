"""Small one-shot MangoWM IPC client; no external mmsg executable required."""
import json
import os
import socket


def request(command, timeout=5):
    if not hasattr(socket, 'AF_UNIX'):
        raise RuntimeError('MangoWM IPC is available on Linux only.')
    path = os.environ.get('MANGO_INSTANCE_SIGNATURE')
    if not path:
        raise RuntimeError('MANGO_INSTANCE_SIGNATURE is not set. Start LPHK from a MangoWM terminal.')
    if '\n' in command or len(command.encode('utf-8')) > 4000:
        raise ValueError('Invalid MangoWM IPC command')
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
            connection.settimeout(timeout)
            connection.connect(path)
            connection.sendall((command + '\n').encode('utf-8'))
            data = bytearray()
            while b'\n' not in data:
                chunk = connection.recv(4096)
                if not chunk:
                    break
                data.extend(chunk)
                if len(data) > 1024 * 1024:
                    raise RuntimeError('MangoWM IPC response is too large')
        text = data.decode('utf-8').split('\n', 1)[0]
        response = json.loads(text)
    except (OSError, UnicodeError, ValueError) as error:
        raise RuntimeError(f'Cannot read MangoWM IPC: {error}') from error
    if isinstance(response, dict) and response.get('error'):
        raise RuntimeError('MangoWM: ' + str(response['error']))
    return text
