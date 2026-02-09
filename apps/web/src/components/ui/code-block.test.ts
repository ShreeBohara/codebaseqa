import { describe, expect, it } from 'vitest'

import { detectLanguage } from './code-block'

describe('detectLanguage', () => {
    it('maps new csharp and cpp extensions', () => {
        expect(detectLanguage('Program.cs')).toBe('csharp')
        expect(detectLanguage('script.csx')).toBe('csharp')
        expect(detectLanguage('main.cpp')).toBe('cpp')
        expect(detectLanguage('core.hh')).toBe('cpp')
        expect(detectLanguage('template.tpp')).toBe('cpp')
    })

    it('maps ruby and rails-related filenames/extensions', () => {
        expect(detectLanguage('Gemfile')).toBe('ruby')
        expect(detectLanguage('Rakefile')).toBe('ruby')
        expect(detectLanguage('jobs/build.rake')).toBe('ruby')
        expect(detectLanguage('my-lib.gemspec')).toBe('ruby')
        expect(detectLanguage('config.ru')).toBe('ruby')
        expect(detectLanguage('app/views/home/index.erb')).toBe('erb')
    })
})
