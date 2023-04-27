module.exports = {
    ci: {
        collect: {
            url: [
                'http://127.0.0.1:8000/dashboard/admin',
                'http://127.0.0.1:8000/workshops/events',
            ],
            startServerCommand: 'pipenv run make serve',
            puppeteerScript: 'puppeteer-script.js',
            numberOfRuns: 1
        },
        upload: {
            target: 'temporary-public-storage'
        },
    },
};