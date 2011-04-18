
"""Test the media accessors.

If run directly from the command line, also tests the accessors and the names
of all the media by getting just about everything in a naive brute-force way.
This, of course, takes a lot of time to run.
"""

import os
import re

from nose.tools import *
from nose.plugins.skip import SkipTest
import nose
import pkg_resources

from pokedex.db import tables, connect, media

session = connect()
basedir = pkg_resources.resource_filename('pokedex', 'data/media')

path_re = re.compile('^[-a-z0-9./]*$')

def test_totodile():
    """Totodile's female sprite -- same as male"""
    totodile = session.query(tables.Pokemon).filter_by(identifier=u'totodile').one()
    accessor = media.PokemonMedia(totodile)
    assert accessor.sprite() == accessor.sprite(female=True)

def test_chimecho():
    """Chimecho's Platinum female backsprite -- diffeent from male"""
    chimecho = session.query(tables.Pokemon).filter_by(identifier=u'chimecho').one()
    accessor = media.PokemonMedia(chimecho)
    male = accessor.sprite('platinum', back=True, frame=2)
    female = accessor.sprite('platinum', back=True, female=True, frame=2)
    assert male != female

def test_venonat():
    """Venonat's shiny Yellow sprite -- same as non-shiny"""
    venonat = session.query(tables.Pokemon).filter_by(identifier=u'venonat').one()
    accessor = media.PokemonMedia(venonat)
    assert accessor.sprite('yellow') == accessor.sprite('yellow', shiny=True)

def test_arceus_icon():
    """Arceus fire-form icon -- same as base icon"""
    arceus = session.query(tables.Pokemon).filter_by(identifier=u'arceus').one()
    accessor = media.PokemonMedia(arceus)
    fire_arceus = [f for f in arceus.forms if f.identifier == 'fire'][0]
    fire_accessor = media.PokemonFormMedia(fire_arceus)
    assert accessor.icon() == fire_accessor.icon()

@raises(ValueError)
def test_strict_castform():
    """Castform rainy form overworld with strict -- unavailable"""
    castform = session.query(tables.Pokemon).filter_by(identifier=u'castform').first()
    rainy_castform = [f for f in castform.forms if f.identifier == 'rainy'][0]
    rainy_castform = media.PokemonFormMedia(rainy_castform)
    rainy_castform.overworld('up', strict=True)

@raises(ValueError)
def test_strict_exeggcute():
    """Exeggcutes's female backsprite, with strict -- unavailable"""
    exeggcute = session.query(tables.Pokemon).filter_by(identifier=u'exeggcute').one()
    accessor = media.PokemonMedia(exeggcute)
    accessor.sprite(female=True, strict=True)



def get_all_filenames():
    print 'Reading all filenames...'

    all_filenames = set()

    for dirpath, dirnames, filenames in os.walk(basedir):
        for filename in filenames:
            path = os.path.join(dirpath, filename)
            assert path_re.match(path), path
            all_filenames.add(path)

    return all_filenames

def hit(filenames, method, *args, **kwargs):
    """
    Run the given accessor method with args & kwargs; if found remove the
    result path from filenames and return True, else return False.
    """
    try:
        medium = method(*args, **kwargs)
        #print 'Hit', medium.relative_path
        assert medium.exists
    except ValueError, e:
        #print 'DNF', e
        return False
    except:
        print 'Error while processing', method, args, kwargs
        raise
    try:
        filenames.remove(medium.path)
    except KeyError:
        pass
    return True

def check_get_everything():
    """
    For every the accessor method, loop over the Cartesian products of all
    possible values for its arguments.
    Make sure we get every file in the repo, and that we get a file whenever
    we should.

    Well, there are exceptions of course.
    """

    versions = list(session.query(tables.Version).all())
    versions.append('red-green')

    black = session.query(tables.Version).filter_by(identifier=u'black').one()

    filenames = get_all_filenames()

    # Some small stuff first

    for damage_class in session.query(tables.MoveDamageClass).all():
        assert hit(filenames, media.DamageClassMedia(damage_class).icon)

    for habitat in session.query(tables.PokemonHabitat).all():
        assert hit(filenames, media.HabitatMedia(habitat).icon)

    for shape in session.query(tables.PokemonShape).all():
        assert hit(filenames, media.ShapeMedia(shape).icon)

    for item_pocket in session.query(tables.ItemPocket).all():
        assert hit(filenames, media.ItemPocketMedia(item_pocket).icon)
        assert hit(filenames, media.ItemPocketMedia(item_pocket).icon, selected=True)

    for contest_type in session.query(tables.ContestType).all():
        assert hit(filenames, media.ContestTypeMedia(contest_type).icon)

    for elemental_type in session.query(tables.Type).all():
        assert hit(filenames, media.TypeMedia(elemental_type).icon)

    # Items
    versions_for_items = [
            None,
            session.query(tables.Version).filter_by(identifier='emerald').one(),
        ]

    for item in session.query(tables.Item).all():
        accessor = media.ItemMedia(item)
        assert hit(filenames, accessor.berry_image) or not item.berry
        for rotation in (0, 90, 180, 270):
            assert hit(filenames, accessor.underground, rotation=rotation) or (
                    not item.appears_underground or rotation)
        for version in versions_for_items:
            success = hit(filenames, accessor.sprite, version=version)
            if version is None:
                assert success

    for color in 'red green blue pale prism'.split():
        for big in (True, False):
            accessor = media.UndergroundSphereMedia(color=color, big=big)
            assert hit(filenames, accessor.underground)

    for rock_type in 'i ii o o-big s t z'.split():
        accessor = media.UndergroundRockMedia(rock_type)
        for rotation in (0, 90, 180, 270):
            success = hit(filenames, accessor.underground, rotation=rotation)
            assert success or rotation

    # Pokemon!
    accessors = []

    accessors.append(media.UnknownPokemonMedia())
    accessors.append(media.EggMedia())
    manaphy = session.query(tables.Pokemon).filter_by(identifier=u'manaphy').one()
    accessors.append(media.EggMedia(manaphy))
    accessors.append(media.SubstituteMedia())

    print 'Loading pokemon'

    for form in session.query(tables.PokemonForm).filter(tables.PokemonForm.identifier != '').all():
        accessors.append(media.PokemonFormMedia(form))

    for pokemon in session.query(tables.Pokemon).all():
        accessors.append(media.PokemonMedia(pokemon))

    for accessor in accessors:
        assert hit(filenames, accessor.footprint) or not accessor.form
        assert hit(filenames, accessor.trozei) or not accessor.form or (
                accessor.form.pokemon.generation.id > 3)
        assert hit(filenames, accessor.cry) or not accessor.form
        assert hit(filenames, accessor.cropped_sprite) or not accessor.form
        for female in (True, False):
            assert hit(filenames, accessor.icon, female=female) or not accessor.form
            assert hit(filenames, accessor.sugimori, female=female) or (
                    not accessor.form or accessor.form.pokemon.id >= 647)
            for shiny in (True, False):
                for frame in (1, 2):
                    for direction in 'up down left right'.split():
                        assert hit(filenames, accessor.overworld,
                                direction=direction,
                                shiny=shiny,
                                female=female,
                                frame=frame,
                            ) or not accessor.form or (
                                    accessor.form.pokemon.generation.id > 4)
                    for version in versions:
                        for animated in (True, False):
                            for back in (True, False):
                                for color in (None, 'gray', 'gbc'):
                                    success = hit(filenames,
                                            accessor.sprite,
                                            version,
                                            animated=animated,
                                            back=back,
                                            color=color,
                                            shiny=shiny,
                                            female=female,
                                            frame=frame,
                                        )
                                    if (version == black and not animated
                                        and not back and not color and not
                                        shiny and not female and
                                        frame == 1):
                                        # All pokemon are in Black
                                        assert success or not accessor.form
                                    if (str(accessor.pokemon_id) == '1'
                                        and not animated and not color and
                                        frame == 1):
                                        # Bulbasaur is in all versions
                                        assert success

    # Remove exceptions
    exceptions = [os.path.join(basedir, dirname) for dirname in
            'chrome fonts ribbons'.split()]
    exceptions.append(os.path.join(basedir, 'items', 'hm-'))
    exceptions = tuple(exceptions)

    for filename in tuple(filenames):
        if filename.startswith(exceptions):
            filenames.remove(filename)

    if len(filenames):
        print
        print '-----------------'
        print 'Unaccessed stuff:'
        for filename in sorted(filenames):
            print filename
        print len(filenames), 'unaccessed files :('

    return (not filenames)

if __name__ == '__main__':
    result = nose.run(defaultTest=__file__)
    result = result and check_get_everything()
    exit(not result)