module.exports = {
    ci: {
        collect: {
            url: ['http://localhost:8000/'],
            startServerCommand: 'pipenv run make serve',
        },
        upload: {
            target: 'temporary-public-storage',
        },
    },
};