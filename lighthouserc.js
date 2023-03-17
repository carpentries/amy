module.exports = {
    ci: {
        collect: {
            url: ['http://127.0.0.1:8000/'],
            puppeteerScript: 'puppeteer-script.js'
        },
        upload: {
            target: 'temporary-public-storage',
        },
    },
};