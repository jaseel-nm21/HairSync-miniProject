from dulwich.repo import Repo
from dulwich import porcelain

repo = Repo('.')

# Set HEAD to 'main'
head_commit = repo.head()
repo.refs[b'refs/heads/main'] = head_commit
repo.refs.set_symbolic_ref(b'HEAD', b'refs/heads/main')
print('HEAD now points to main:', head_commit.decode('ascii'))

# Add remote origin
remote_url = 'https://github.com/jaseel-nm21/hairSync.git'
try:
    porcelain.remote_add('.', 'origin', remote_url)
    print('Remote origin added:', remote_url)
except Exception as e:
    print('Remote note:', e)

print('[+] Remote configured for https://github.com/jaseel-nm21/hairSync.git')
