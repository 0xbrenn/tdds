module.exports = {

  apps: [

    {

      name: 'iopn-backend',

      cwd: '/var/www/badge/backend',

      script: 'venv/bin/uvicorn',

      args: 'main:app --host 0.0.0.0 --port 8000',

      interpreter: 'none',

      env: {

        PATH: '/var/www/badge/backend/venv/bin:/usr/bin',

      }

    }

  ]

};
