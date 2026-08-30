package com.opensilkroadmap.app.game;

import static org.junit.Assert.assertEquals;

import org.junit.Test;

public class EntityTest {

  @Test
  public void carriesIdentityAndName() {
    Entity entity = new Entity("42", "Black Tortoise");
    assertEquals("42", entity.id());
    assertEquals("Black Tortoise", entity.name());
  }

  @Test
  public void positionIsNeutralWorldCoordinates() {
    Entity entity = new Entity("1", "e");
    entity.setPosition(100.0, 200.0, 0.0);
    assertEquals(100.0, entity.x(), 1e-9);
    assertEquals(200.0, entity.y(), 1e-9);
    assertEquals(0.0, entity.z(), 1e-9);
  }
}
