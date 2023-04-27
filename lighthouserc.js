module.exports = {
    ci: {
        collect: {
            url: [
                'http://127.0.0.1:8000/dashboard/admin/',
                'http://127.0.0.1:8000/communityroles/role/1/edit/',
                'http://127.0.0.1:8000/dashboard/instructor/autoupdate_profile/',
                'http://127.0.0.1:8000/dashboard/instructor/',
                'http://127.0.0.1:8000/dashboard/admin/search/',
                'http://127.0.0.1:8000/dashboard/instructor/training_progress/',
                'http://127.0.0.1:8000/dashboard/instructor/teaching_opportunities/',
                'http://127.0.0.1:8000/account/password_reset/',
                'http://127.0.0.1:8000/forms/workshop/',
                'http://127.0.0.1:8000/requests/workshop_requests/',
                'http://127.0.0.1:8000/requests/selforganised_submission/1/',
                'http://127.0.0.1:8000/requests/training_request/1/',
                'http://127.0.0.1:8000/requests/workshop_request/1/set_state/pending/',
                'http://127.0.0.1:8000/requests/workshop_request/2/set_state/discarded/',
                'http://127.0.0.1:8000/requests/workshop_request/1/edit/',
                'http://127.0.0.1:8000/requests/workshop_request/1/accept_event/',
                'http://127.0.0.1:8000/fiscal/membership/1/members/',
                'http://127.0.0.1:8000/recruitment/process/1/add-signup/',
                'http://127.0.0.1:8000/recruitment/processes/',
                'http://127.0.0.1:8000/trainings/trainees/',
                'http://127.0.0.1:8000/workshops/events/',
                'http://127.0.0.1:8000/workshops/persons/',
                'http://127.0.0.1:8000/workshops/log/',
                'http://127.0.0.1:8000/workshops/events/metadata_changed/',
                'http://127.0.0.1:8000/workshops/person/1/',
                'http://127.0.0.1:8000/workshops/persons/add/',
                'http://127.0.0.1:8000/workshops/persons/merge/?person_a=2&person_b=3',
                'http://127.0.0.1:8000/workshops/task/1/',
            ],
            startServerCommand: 'pipenv run make serve',
            puppeteerScript: 'puppeteer-script.js',
            numberOfRuns: 1
        },
        upload: {
            target: 'filesystem',
            outputDir: 'lighthouse-ci-report'
        },

        assert: {
            assertions: {
                "categories:accessibility": ["error", { "minScore": 1 }]
            }
        }
    }
};